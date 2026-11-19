@echo off
set SDK=C:\Users\jnewt\AppData\Local\Android\Sdk
set BT=%SDK%\build-tools\35.0.0
set JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot
if not exist build mkdir build
"%BT%\aapt.exe" package -f -M AndroidManifest.xml -I "%SDK%\platforms\android-35\android.jar" -F build\unsigned.apk
if errorlevel 1 exit /b 1
"%JAVA_HOME%\bin\javac.exe" -source 8 -target 8 -cp "%SDK%\platforms\android-35\android.jar" -d build src\org\sailinguk\racecam\MainActivity.java src\org\sailinguk\racecam\RaceCamMqttTelemetry.java src\org\sailinguk\racecam\RaceStartClock.java src\org\sailinguk\racecam\RaceControlVerifier.java
if errorlevel 1 exit /b 1
call "%BT%\d8.bat" --lib "%SDK%\platforms\android-35\android.jar" --output build build\org\sailinguk\racecam\*.class
if errorlevel 1 exit /b 1
copy /y build\classes.dex classes.dex >nul
"%BT%\aapt.exe" add build\unsigned.apk classes.dex
if errorlevel 1 exit /b 1
"%BT%\zipalign.exe" -f 4 build\unsigned.apk build\aligned.apk
if errorlevel 1 exit /b 1
if not exist build\racecam-test.keystore "%JAVA_HOME%\bin\keytool.exe" -genkeypair -keystore build\racecam-test.keystore -storepass android -keypass android -alias test -keyalg RSA -keysize 2048 -validity 3650 -dname "CN=Sailing UK RaceCam Test"
"%BT%\apksigner.bat" sign --ks build\racecam-test.keystore --ks-key-alias test --ks-pass pass:android --key-pass pass:android --out build\RaceCam-POC.apk build\aligned.apk
if errorlevel 1 exit /b 1
"%BT%\apksigner.bat" verify build\RaceCam-POC.apk
