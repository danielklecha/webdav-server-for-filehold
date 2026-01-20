# IIS deployment

## Prerequisites

1. Install package  manager - uv is recommended
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
2. Install handler:
   - ASP.NET Core Module (ANCM) - install ASP.NET Core 2.0+ Runtime Hosting Bundle from [here](https://dotnet.microsoft.com/en-us/download/dotnet)
   - ASP.NET Core Module (ANCMV2) - install ASP.NET Core 2.2+ Runtime Hosting Bundle from [here](https://dotnet.microsoft.com/en-us/download/dotnet)
   - HttpPlatformHandler - install from [here](https://www.iis.net/downloads/microsoft/httpplatformhandler)

## Installation

1. Create deployment directory `C:\inetpub\wwwroot\webdav`
2. Copy WHL file to deployment directory
3. Open deployment directory in PowerShell
4. Create virtual environment in `uv venv`
5. Install the WHL file in the virtual environment `uv pip install webdav_server_for_filehold-1.0.0-py3-none-any.whl`
6. Create a log directory in the deployment directory `mkdir logs`
7. Create a new application pool in IIS
- Name it `webdav AppPool`
- Set the .NET CLR version to `No Managed Code`
- Set the Managed Pipeline Mode to `Integrated`
8.  Create a new website in IIS
- Name it `webdav`
- Set the physical path to `C:\inetpub\wwwroot\webdav`
- Set the application pool to `webdav AppPool`
9.  Create a web.config file in the deployment directory

## Website configuration

### Option 1 - subdomain

1. In the Connections pane on the left, right-click Sites and select Add Website...
2. In the Add Website dialog, enter the following:
- Site name: `webdav.localhost`
- Application pool: `webdav AppPool`
- Physical path: `C:\inetpub\wwwroot\webdav`
- Type: `http`
- IP Address: `All Unassigned`
- Port: `80`
- Host name: `webdav.localhost`

### Option 2 - subdirectory

1. In the Connections pane on the left, expand `Sites`, right-click `Default Web Site` and select Add Application...
2. In the Add Application dialog, enter the following:
- Alias: `webdav`
- Application pool: `webdav AppPool`
- Physical path: `C:\inetpub\wwwroot\webdav`

## web.config configuration


### ASP.NET Core Module (ANCMV2) - recommended

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
                stdoutLogFile=".\logs\python-ancmv2-stdout">
      <environmentVariables>
        <environmentVariable name="PYTHONPATH" value=".\" />
        <environmentVariable name="WEBDAV_FILEHOLD_URL" value="http://localhost/FH/FileHold/" />
        <environmentVariable name="WEBDAV_DEFAULT_SCHEMA_NAME" value="ed" />
      </environmentVariables>    
    </aspNetCore>
  </system.webServer>
</configuration>
```

### ASP.NET Core Module (ANCM)

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="aspNetCore" path="*" verb="*" modules="AspNetCoreModule" resourceType="Unspecified" />
    </handlers>
    <aspNetCore processPath="C:\inetpub\wwwroot\webdav\.venv\Scripts\python.exe" 
                arguments="-m uvicorn webdav_server_for_filehold.main:get_wsgi_app --port %ASPNETCORE_PORT% --interface wsgi --host 127.0.0.1"
                stdoutLogEnabled="true" 
                stdoutLogFile=".\logs\python-ancm-stdout">
      <environmentVariables>
        <environmentVariable name="PYTHONPATH" value=".\" />
        <environmentVariable name="WEBDAV_FILEHOLD_URL" value="http://localhost/FH/FileHold/" />
        <environmentVariable name="WEBDAV_DEFAULT_SCHEMA_NAME" value="ed" />
      </environmentVariables>    
    </aspNetCore>
  </system.webServer>
</configuration>
```

### HttpPlatformHandler

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="PythonHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified"/>
    </handlers>
    <httpPlatform processPath="C:\inetpub\wwwroot\webdav\.venv\Scripts\python.exe" 
                  arguments="-m uvicorn webdav_server_for_filehold.main:get_wsgi_app --port %HTTP_PLATFORM_PORT% --interface wsgi --host 127.0.0.1"
                  stdoutLogEnabled="true"
                  stdoutLogFile="..\logs\python-httpplatform-stdout">
      <environmentVariables>
        <environmentVariable name="PYTHONPATH" value=".\" />
        <environmentVariable name="WEBDAV_FILEHOLD_URL" value="http://localhost/FH/FileHold/" />
        <environmentVariable name="WEBDAV_DEFAULT_SCHEMA_NAME" value="ed" />
      </environmentVariables>
    </httpPlatform>
  </system.webServer>
</configuration>
```

## web.config post-configuration

If you selected **Option 2 (subdirectory)**, add the following to the `web.config` file inside the `<environmentVariables>` section:

```xml
<environmentVariable name="WEBDAV_MOUNT_PATH" value="/webdav" />
<environmentVariable name="SCRIPT_NAME" value="/webdav" />
```

## Permissions

1.  Set permissions for deployment directory
```powershell
icacls "C:\inetpub\wwwroot\webdav" /reset /T /Q
icacls "C:\inetpub\wwwroot\webdav" /grant "IIS_IUSRS:(OI)(CI)M" /T /Q
icacls "C:\inetpub\wwwroot\webdav" /grant "IUSR:(OI)(CI)RX" /T /Q
```
2.  Set permissions for python directory (path changes based on installation)
```powershell
icacls "$env:LOCALAPPDATA\Python" /reset /T /Q
icacls "$env:LOCALAPPDATA\Python" /grant "IIS_IUSRS:(OI)(CI)M" /T /Q
icacls "$env:LOCALAPPDATA\Python" /grant "IUSR:(OI)(CI)RX" /T /Q
```
3.  Set permissions for uv directory (path changes based on installation)
```powershell
icacls "$env:APPDATA\uv\python" /reset /T /Q
icacls "$env:APPDATA\uv\python" /grant "IIS_IUSRS:(OI)(CI)M" /T /Q
icacls "$env:APPDATA\uv\python" /grant "IUSR:(OI)(CI)RX" /T /Q
```
4.  Restart IIS: `iisreset`
