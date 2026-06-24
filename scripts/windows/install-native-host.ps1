param(
    [Parameter(Mandatory = $false)]
    [string]$ExtensionId,

    [Parameter(Mandatory = $false)]
    [string]$Browser,

    [Parameter(Mandatory = $false)]
    [string]$BridgeUrl = ""
)

$ErrorActionPreference = "Stop"

$HostName = "com.cuiguidong.browserbridge"
$InstallDir = Join-Path $env:LOCALAPPDATA "BrowserBridge\NativeHost"
$ManifestPath = Join-Path $InstallDir "$HostName.json"
$LauncherSourcePath = Join-Path $InstallDir "browser-bridge-native-host.cs"
$WrapperPath = Join-Path $InstallDir "browser-bridge-native-host.exe"
$LegacyCmdPath = Join-Path $InstallDir "browser-bridge-native-host.cmd"
$LogPath = Join-Path $InstallDir "browser-bridge-native-host.log"

function Prompt-IfMissing {
    param(
        [string]$Value,
        [string]$Prompt
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return Read-Host $Prompt
    }
    return $Value
}

$ExtensionId = Prompt-IfMissing $ExtensionId "Extension id from chrome://extensions or edge://extensions"
$Browser = Prompt-IfMissing $Browser "Browser to register (edge/chrome/both)"
$Browser = $Browser.Trim().ToLowerInvariant()
$BridgeUrl = if ([string]::IsNullOrWhiteSpace($BridgeUrl)) { "http://127.0.0.1:17777" } else { $BridgeUrl.TrimEnd("/") }

if ([string]::IsNullOrWhiteSpace($ExtensionId)) {
    throw "ExtensionId is required."
}

if (@("edge", "chrome", "both") -notcontains $Browser) {
    throw "Browser must be one of: edge, chrome, both."
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$escapedBridgeUrl = $BridgeUrl.Replace("\", "\\").Replace('"', '\"')
$escapedLogPath = $LogPath.Replace("\", "\\").Replace('"', '\"')

$launcherSource = @"
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Collections.Generic;

class BrowserBridgeNativeHost
{
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
    static readonly object StdoutLock = new object();
    static string SessionId = null;

    static int Main()
    {
        string bridgeUrl = "$escapedBridgeUrl";
        string logPath = "$escapedLogPath";

        try
        {
            Log(logPath, "started");
            if (!RegisterSession(bridgeUrl, logPath))
            {
                Log(logPath, "register failed");
                return 1;
            }

            Thread pullThread = new Thread(() => PullLoop(bridgeUrl, logPath));
            pullThread.IsBackground = true;
            pullThread.Start();

            ReadLoop(bridgeUrl, logPath);
            return 0;
        }
        catch (Exception ex)
        {
            Log(logPath, "fatal: " + ex);
            return 1;
        }
        finally
        {
            UnregisterSession(bridgeUrl, logPath);
            Log(logPath, "exited");
        }
    }

    static bool RegisterSession(string bridgeUrl, string logPath)
    {
        object resp = PostJson(bridgeUrl + "/native/session/register", "{\"type\":\"extension\"}", 30, logPath);
        Dictionary<string, object> envelope = resp as Dictionary<string, object>;
        if (envelope == null || !envelope.ContainsKey("ok") || !(bool)envelope["ok"])
        {
            return false;
        }
        Dictionary<string, object> data = envelope["data"] as Dictionary<string, object>;
        if (data == null || !data.ContainsKey("sessionId"))
        {
            return false;
        }
        SessionId = Convert.ToString(data["sessionId"]);
        Log(logPath, "registered session " + SessionId);
        return true;
    }

    static void UnregisterSession(string bridgeUrl, string logPath)
    {
        if (String.IsNullOrEmpty(SessionId)) return;
        try
        {
            PostJson(bridgeUrl + "/native/session/unregister?sessionId=" + Uri.EscapeDataString(SessionId), "{}", 10, logPath);
        }
        catch (Exception ex)
        {
            Log(logPath, "unregister error: " + ex.Message);
        }
    }

    static void PullLoop(string bridgeUrl, string logPath)
    {
        while (!String.IsNullOrEmpty(SessionId))
        {
            try
            {
                string url = bridgeUrl + "/native/session/pull?sessionId=" + Uri.EscapeDataString(SessionId) + "&timeoutSeconds=25";
                object resp = GetJson(url, 30, logPath);
                Dictionary<string, object> envelope = resp as Dictionary<string, object>;
                if (envelope == null || !envelope.ContainsKey("ok") || !(bool)envelope["ok"])
                {
                    Thread.Sleep(1000);
                    continue;
                }
                Dictionary<string, object> data = envelope["data"] as Dictionary<string, object>;
                if (data == null || !data.ContainsKey("command") || data["command"] == null)
                {
                    Thread.Sleep(1000);
                    continue;
                }
                WriteNativeMessage(data["command"]);
            }
            catch (Exception ex)
            {
                Log(logPath, "pull error: " + ex.Message);
                Thread.Sleep(2000);
            }
        }
    }

    static void ReadLoop(string bridgeUrl, string logPath)
    {
        Stream input = Console.OpenStandardInput();
        while (true)
        {
            byte[] lengthBytes = ReadExactly(input, 4);
            if (lengthBytes == null) break;
            int length = BitConverter.ToInt32(lengthBytes, 0);
            if (length <= 0 || length > 64 * 1024 * 1024)
            {
                Log(logPath, "invalid native message length: " + length);
                break;
            }
            byte[] payload = ReadExactly(input, length);
            if (payload == null) break;
            string json = Encoding.UTF8.GetString(payload);
            if (String.IsNullOrEmpty(SessionId)) continue;
            string body = "{\"sessionId\":" + Json.Serialize(SessionId) + ",\"message\":" + json + "}";
            try
            {
                PostJson(bridgeUrl + "/native/session/result", body, 10, logPath);
            }
            catch (Exception ex)
            {
                Log(logPath, "result post error: " + ex.Message);
            }
        }
    }

    static byte[] ReadExactly(Stream stream, int length)
    {
        byte[] buffer = new byte[length];
        int offset = 0;
        while (offset < length)
        {
            int read = stream.Read(buffer, offset, length - offset);
            if (read <= 0) return null;
            offset += read;
        }
        return buffer;
    }

    static void WriteNativeMessage(object message)
    {
        string json = Json.Serialize(message);
        byte[] payload = Encoding.UTF8.GetBytes(json);
        byte[] length = BitConverter.GetBytes(payload.Length);
        lock (StdoutLock)
        {
            Stream output = Console.OpenStandardOutput();
            output.Write(length, 0, length.Length);
            output.Write(payload, 0, payload.Length);
            output.Flush();
        }
    }

    static object GetJson(string url, int timeoutSeconds, string logPath)
    {
        HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
        request.Method = "GET";
        request.Timeout = timeoutSeconds * 1000;
        using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
        using (StreamReader reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
        {
            return Json.DeserializeObject(reader.ReadToEnd());
        }
    }

    static object PostJson(string url, string body, int timeoutSeconds, string logPath)
    {
        byte[] bytes = Encoding.UTF8.GetBytes(body);
        HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
        request.Method = "POST";
        request.Timeout = timeoutSeconds * 1000;
        request.ContentType = "application/json";
        request.ContentLength = bytes.Length;
        using (Stream stream = request.GetRequestStream())
        {
            stream.Write(bytes, 0, bytes.Length);
        }
        using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
        using (StreamReader reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
        {
            return Json.DeserializeObject(reader.ReadToEnd());
        }
    }

    static void Log(string logPath, string message)
    {
        try
        {
            File.AppendAllText(logPath, "[native-host] " + DateTime.Now.ToString("s") + " " + message + Environment.NewLine, new UTF8Encoding(false));
        }
        catch
        {
        }
    }
}
"@
Set-Content -Path $LauncherSourcePath -Value $launcherSource -Encoding ASCII

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (!(Test-Path $csc)) {
    throw "C# compiler not found at $csc. Install .NET Framework build tools or provide a prebuilt native host launcher."
}
& $csc /nologo /target:exe /reference:System.Web.Extensions.dll /out:$WrapperPath $LauncherSourcePath
Remove-Item -Force -ErrorAction SilentlyContinue $LauncherSourcePath
Remove-Item -Force -ErrorAction SilentlyContinue $LegacyCmdPath

$manifest = [ordered]@{
    name = $HostName
    description = "Browser Bridge native messaging host"
    type = "stdio"
    path = $WrapperPath
    allowed_origins = @("chrome-extension://$ExtensionId/")
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $ManifestPath -Encoding ASCII

function Install-RegistryKey {
    param([string]$BrowserName)

    if ($BrowserName -eq "chrome") {
        $keyPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"
    } elseif ($BrowserName -eq "edge") {
        $keyPath = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName"
    } else {
        throw "Unsupported browser: $BrowserName"
    }

    New-Item -Path $keyPath -Force | Out-Null
    Set-Item -Path $keyPath -Value $ManifestPath
    Write-Host "Installed $BrowserName native host registry key: $keyPath"
}

if ($Browser -eq "chrome" -or $Browser -eq "both") {
    Install-RegistryKey "chrome"
}
if ($Browser -eq "edge" -or $Browser -eq "both") {
    Install-RegistryKey "edge"
}

Write-Host ""
Write-Host "Native host manifest: $ManifestPath"
Write-Host "Native host launcher: $WrapperPath"
Write-Host "Log file:             $LogPath"
Write-Host "Reload the Browser Bridge extension, then run ./scripts/doctor.sh inside WSL."
