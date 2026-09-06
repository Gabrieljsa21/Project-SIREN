' Lanca o iniciar_siren.bat com a janela do console totalmente escondida - o .bat em
' si ja sobe o processo real (siren.main) escondido via pythonw, mas o CONSOLE DO
' PROPRIO .bat (cmd.exe processando o script) sempre aparece quando aberto direto
' (ex.: atalho da area de trabalho, ou item da categoria Projects do IRIS). Esse
' .vbs existe so pra esconder esse console tambem - mesmo padrao do
' iniciar_echo_oculto.vbs/iniciar_iris_oculto.vbs.
'
' A janela do player em si (Leve ou Completo) continua aparecendo normalmente -
' isso so esconde o console do launcher, nunca a interface grafica do SIREN.

Set objShell = CreateObject("WScript.Shell")
Set oFso = CreateObject("Scripting.FileSystemObject")
strPastaAtual = oFso.GetParentFolderName(WScript.ScriptFullName)
objShell.Run """" & strPastaAtual & "\iniciar_siren.bat""", 0, False
