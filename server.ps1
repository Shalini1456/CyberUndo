$port = 8080
$path = Join-Path $PSScriptRoot "frontend"
if (-not (Test-Path $path)) {
    $path = $PSScriptRoot
}

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $port)
$listener.Start()
Write-Output "CyberUndo HTTP Server listening on http://localhost:$port (serving from $path)"

while ($true) {
    try {
        $client = $listener.AcceptTcpClient()
        $stream = $client.GetStream()
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::ASCII)
        
        $requestLine = $reader.ReadLine()
        if (-not [string]::IsNullOrEmpty($requestLine)) {
            $tokens = $requestLine.Split(' ')
            if ($tokens.Length -ge 2) {
                $rawUrl = $tokens[1]
                $urlPath = $rawUrl.Split('?')[0].TrimStart('/')
                if ([string]::IsNullOrWhiteSpace($urlPath)) {
                    $urlPath = "index.html"
                }

                $filePath = Join-Path $path $urlPath

                if (Test-Path $filePath -PathType Leaf) {
                    $bytes = [System.IO.File]::ReadAllBytes($filePath)
                    $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
                    
                    $contentType = switch ($ext) {
                        ".html" { "text/html; charset=utf-8" }
                        ".htm"  { "text/html; charset=utf-8" }
                        ".css"  { "text/css; charset=utf-8" }
                        ".js"   { "application/javascript; charset=utf-8" }
                        ".json" { "application/json" }
                        ".png"  { "image/png" }
                        ".jpg"  { "image/jpeg" }
                        ".svg"  { "image/svg+xml" }
                        default { "text/html; charset=utf-8" }
                    }

                    $header = "HTTP/1.1 200 OK`r`nContent-Type: $contentType`r`nContent-Length: $($bytes.Length)`r`nAccess-Control-Allow-Origin: *`r`nConnection: close`r`n`r`n"
                    $headerBytes = [System.Text.Encoding]::UTF8.GetBytes($header)
                    $stream.Write($headerBytes, 0, $headerBytes.Length)
                    $stream.Write($bytes, 0, $bytes.Length)
                } else {
                    $msg = "404 Not Found"
                    $msgBytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
                    $header = "HTTP/1.1 404 Not Found`r`nContent-Type: text/plain`r`nContent-Length: $($msgBytes.Length)`r`nConnection: close`r`n`r`n"
                    $headerBytes = [System.Text.Encoding]::UTF8.GetBytes($header)
                    $stream.Write($headerBytes, 0, $headerBytes.Length)
                    $stream.Write($msgBytes, 0, $msgBytes.Length)
                }
            }
        }
        $stream.Flush()
        $client.Close()
    } catch {
        # continue loop
    }
}
