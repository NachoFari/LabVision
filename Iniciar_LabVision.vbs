Option Explicit

Dim WshShell, fso, scriptDir, userProfile, localAppData, candidatePaths, pythonwPath, i
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
localAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")

candidatePaths = Array( _
    "C:\Users\farin\.venv\Scripts\pythonw.exe", _
    userProfile & "\.venv\Scripts\pythonw.exe", _
    scriptDir & "\.venv\Scripts\pythonw.exe", _
    localAppData & "\Programs\Python\Python312\pythonw.exe", _
    localAppData & "\Programs\Python\Python311\pythonw.exe", _
    localAppData & "\Programs\Python\Python310\pythonw.exe", _
    "C:\Python312\pythonw.exe", _
    "C:\Python311\pythonw.exe", _
    "C:\Python310\pythonw.exe", _
    "C:\Program Files\Python312\pythonw.exe", _
    "C:\Program Files\Python311\pythonw.exe" _
)

pythonwPath = ""

For i = 0 To UBound(candidatePaths)
    If fso.FileExists(candidatePaths(i)) Then
        pythonwPath = candidatePaths(i)
        Exit For
    End If
Next

' Si no esta en las rutas conocidas, buscar pythonw.exe en cada directorio del PATH
If pythonwPath = "" Then
    Dim envPath, pathArr, p
    envPath = WshShell.ExpandEnvironmentStrings("%PATH%")
    pathArr = Split(envPath, ";")
    For Each p In pathArr
        p = Trim(p)
        If p <> "" Then
            If Right(p, 1) <> "\" Then p = p & "\"
            If fso.FileExists(p & "pythonw.exe") Then
                pythonwPath = p & "pythonw.exe"
                Exit For
            End If
        End If
    Next
End If

' Fallback predeterminado
If pythonwPath = "" Then
    pythonwPath = "pythonw.exe"
End If

' El parametro 0 ejecuta de forma 100% silenciosa y oculta (sin ventana de consola negra)
On Error Resume Next
WshShell.Run """" & pythonwPath & """ """ & scriptDir & "\app.py""", 0, False

If Err.Number <> 0 Then
    MsgBox "No se pudo iniciar LabVision." & vbCrLf & _
           "Detalle: " & Err.Description & vbCrLf & vbCrLf & _
           "Por favor, ejecute 'Instalador_LabVision.bat' para configurar el entorno.", _
           16, "LabVision - Error al Iniciar"
End If

