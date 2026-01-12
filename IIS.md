# IIS deployment

1. Install ASP.NET Core Runtime Hosting Bundle
2. Create deployment directory `C:\inetpub\wwwroot\webdav`
3. Open deployment directory in PowerShell
4. Create virtual environment in `uv venv`
5. Install the WHL file in the virtual environment `uv pip install webdav_server_for_filehold-1.0.0-py3-none-any.whl`
6. Create a web.config file in the deployment directory with the following content:
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="aspNetCore" path="*" verb="*" modules="AspNetCoreModuleV2" resourceType="Unspecified" />
    </handlers>
    <aspNetCore processPath="C:\inetpub\wwwroot\webdav\.venv\Scripts\python.exe" 
                arguments="-m uvicorn webdav_server_for_filehold.main:get_wsgi_app --port %ASPNETCORE_PORT% --interface wsgi --host 127.0.0.1"
                stdoutLogEnabled="true" 
                stdoutLogFile=".\logs\python-anvmv2-stdout">
      <environmentVariables>
        <environmentVariable name="PYTHONPATH" value=".\" />
        <environmentVariable name="WEBDAV_FILEHOLD_URL" value="http://localhost/CH/FileHold/" />
        <environmentVariable name="WEBDAV_DEFAULT_SCHEMA_NAME" value="ed" />
        <environmentVariable name="WEBDAV_MOUNT_PATH" value="/webdav" />
        <environmentVariable name="SCRIPT_NAME" value="/webdav" />
      </environmentVariables>    
    </aspNetCore>
  </system.webServer>
</configuration>
```
7. Create a log directory in the deployment directory `mkdir logs`
8. Create a new application pool in IIS
- Name it `webdav AppPool`
- Set the .NET CLR version to `No Managed Code`
- Set the Managed Pipeline Mode to `Integrated`
9. Create a new website in IIS
- Name it `webdav`
- Set the physical path to `C:\inetpub\wwwroot\webdav`
- Set the application pool to `webdav AppPool`
10. Set permissions for deployment directory
```powershell
icacls "C:\inetpub\wwwroot\webdav" /reset /T /Q
icacls "C:\inetpub\wwwroot\webdav" /grant "IIS_IUSRS:(OI)(CI)M" /T /Q
icacls "C:\inetpub\wwwroot\webdav" /grant "IUSR:(OI)(CI)RX" /T /Q
```
11. Set permissions for python directory (path changes based on installation)
```powershell
icacls "$env:LOCALAPPDATA\Python" /reset /T /Q
icacls "$env:LOCALAPPDATA\Python" /grant "IIS_IUSRS:(OI)(CI)M" /T /Q
icacls "$env:LOCALAPPDATA\Python" /grant "IUSR:(OI)(CI)RX" /T /Q
```
12. Set permissions for uv directory (path changes based on installation)
```powershell
icacls "$env:APPDATA\uv\python" /reset /T /Q
icacls "$env:APPDATA\uv\python" /grant "IIS_IUSRS:(OI)(CI)M" /T /Q
icacls "$env:APPDATA\uv\python" /grant "IUSR:(OI)(CI)RX" /T /Q
```
13. Restart IIS: `iisreset`
