using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Windows.Forms;
using System.Reflection;
using System.Runtime.InteropServices;

[assembly: AssemblyTitle("LabVision")]
[assembly: AssemblyDescription("Digitalización Inteligente de Pantallas de Laboratorio")]
[assembly: AssemblyCompany("NachoFari")]
[assembly: AssemblyProduct("LabVision")]
[assembly: AssemblyCopyright("Copyright © 2026 NachoFari")]
[assembly: AssemblyVersion("0.8.0.0")]
[assembly: AssemblyFileVersion("0.8.0.0")]

namespace LabVisionLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                // Determinar directorio base de la aplicación
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string appPy = Path.Combine(baseDir, "app.py");

                if (!File.Exists(appPy))
                {
                    // Fallback a directorio de trabajo actual si se ejecuta desde otro contexto
                    if (File.Exists(Path.Combine(Directory.GetCurrentDirectory(), "app.py")))
                    {
                        baseDir = Directory.GetCurrentDirectory();
                        appPy = Path.Combine(baseDir, "app.py");
                    }
                    else
                    {
                        MessageBox.Show(
                            "No se encontró el archivo principal 'app.py' en:\n" + baseDir,
                            "LabVision - Error",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Error);
                        return;
                    }
                }

                string pythonPath = null;
                string runtimeDir = Path.Combine(baseDir, "runtime");

                // =========================================================================
                // PRIORIDAD #1: Python portable local incluido en baseDir\runtime
                // =========================================================================
                string localRuntimeW = Path.Combine(runtimeDir, "pythonw.exe");
                string localRuntime = Path.Combine(runtimeDir, "python.exe");

                if (File.Exists(localRuntimeW))
                {
                    pythonPath = localRuntimeW;
                }
                else if (File.Exists(localRuntime))
                {
                    pythonPath = localRuntime;
                }

                // =========================================================================
                // PRIORIDAD #2: Entorno virtual local (.venv en baseDir)
                // =========================================================================
                if (string.IsNullOrEmpty(pythonPath))
                {
                    string localVenvW = Path.Combine(baseDir, @".venv\Scripts\pythonw.exe");
                    string localVenv = Path.Combine(baseDir, @".venv\Scripts\python.exe");
                    if (File.Exists(localVenvW))
                    {
                        pythonPath = localVenvW;
                    }
                    else if (File.Exists(localVenv))
                    {
                        pythonPath = localVenv;
                    }
                }

                // =========================================================================
                // PRIORIDAD #3: Entornos virtuales y Python instalados en el sistema
                // =========================================================================
                if (string.IsNullOrEmpty(pythonPath))
                {
                    string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                    string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

                    string[] candidates = new string[]
                    {
                        Path.Combine(userProfile, @".venv\Scripts\pythonw.exe"),
                        Path.Combine(userProfile, @".venv\Scripts\python.exe"),
                        Path.Combine(localAppData, @"Programs\Python\Python312\pythonw.exe"),
                        Path.Combine(localAppData, @"Programs\Python\Python312\python.exe"),
                        Path.Combine(localAppData, @"Programs\Python\Python311\pythonw.exe"),
                        Path.Combine(localAppData, @"Programs\Python\Python311\python.exe"),
                        Path.Combine(localAppData, @"Programs\Python\Python310\pythonw.exe"),
                        Path.Combine(localAppData, @"Programs\Python\Python310\python.exe"),
                        @"C:\Python312\pythonw.exe",
                        @"C:\Python312\python.exe",
                        @"C:\Python311\pythonw.exe",
                        @"C:\Python311\python.exe",
                        @"C:\Python310\pythonw.exe",
                        @"C:\Python310\python.exe",
                        @"C:\Program Files\Python312\pythonw.exe",
                        @"C:\Program Files\Python312\python.exe",
                        @"C:\Program Files\Python311\pythonw.exe",
                        @"C:\Program Files\Python311\python.exe",
                        @"C:\Program Files\Python310\pythonw.exe",
                        @"C:\Program Files\Python310\python.exe"
                    };

                    foreach (string c in candidates)
                    {
                        if (File.Exists(c))
                        {
                            pythonPath = c;
                            break;
                        }
                    }
                }

                // =========================================================================
                // PRIORIDAD #4: Búsqueda dinámica en el PATH del sistema
                // =========================================================================
                if (string.IsNullOrEmpty(pythonPath))
                {
                    string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
                    foreach (string p in pathEnv.Split(';'))
                    {
                        string trimmed = p.Trim();
                        if (string.IsNullOrEmpty(trimmed)) continue;

                        string targetW = Path.Combine(trimmed, "pythonw.exe");
                        if (File.Exists(targetW))
                        {
                            pythonPath = targetW;
                            break;
                        }

                        string target = Path.Combine(trimmed, "python.exe");
                        if (File.Exists(target))
                        {
                            pythonPath = target;
                            break;
                        }
                    }
                }

                // Si no se encontró ningún intérprete de Python, advertir al usuario
                if (string.IsNullOrEmpty(pythonPath))
                {
                    DialogResult res = MessageBox.Show(
                        "No se encontró un entorno de Python compatible para iniciar LabVision.\n\n" +
                        "Se esperaba el runtime en:\n" + runtimeDir + "\n\n" +
                        "¿Desea ejecutar el instalador automatizado ahora?",
                        "LabVision - Instalación Requerida",
                        MessageBoxButtons.YesNo,
                        MessageBoxIcon.Warning);

                    if (res == DialogResult.Yes)
                    {
                        string installerBat = Path.Combine(baseDir, "Instalador_LabVision.bat");
                        if (File.Exists(installerBat))
                        {
                            Process.Start(new ProcessStartInfo
                            {
                                FileName = installerBat,
                                WorkingDirectory = baseDir,
                                UseShellExecute = true
                            });
                        }
                        else
                        {
                            MessageBox.Show(
                                "No se encontró el instalador automatizado:\n" + installerBat,
                                "LabVision - Error",
                                MessageBoxButtons.OK,
                                MessageBoxIcon.Error);
                        }
                    }
                    return;
                }

                // =========================================================================
                // Configurar inicio del proceso y aislamiento completo de entorno
                // =========================================================================
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonPath;

                // Propagar argumentos de línea de comandos si existen
                if (args != null && args.Length > 0)
                {
                    StringBuilder sbArgs = new StringBuilder();
                    sbArgs.Append("\"").Append(appPy).Append("\"");
                    foreach (string arg in args)
                    {
                        sbArgs.Append(" \"").Append(arg.Replace("\"", "\\\"")).Append("\"");
                    }
                    psi.Arguments = sbArgs.ToString();
                }
                else
                {
                    psi.Arguments = "\"" + appPy + "\"";
                }

                psi.WorkingDirectory = baseDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = false;
                psi.WindowStyle = ProcessWindowStyle.Normal;

                // Configurar variables de entorno para aislamiento completo
                if (Directory.Exists(runtimeDir))
                {
                    psi.EnvironmentVariables["PYTHONHOME"] = runtimeDir;
                    string currentPath = Environment.GetEnvironmentVariable("PATH") ?? "";
                    psi.EnvironmentVariables["PATH"] = runtimeDir + ";" + Path.Combine(runtimeDir, "Scripts") + ";" + currentPath;
                }
                psi.EnvironmentVariables["PYTHONPATH"] = baseDir;

                // =========================================================================
                // Iniciar proceso y verificar fallas tempranas de ejecución
                // =========================================================================
                Process proc = null;
                try
                {
                    proc = Process.Start(psi);
                }
                catch (Exception ex)
                {
                    MessageBox.Show(
                        "Error al iniciar el ejecutable de Python:\n" + pythonPath + "\n\nDetalle: " + ex.Message,
                        "LabVision - Error al Iniciar",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                    return;
                }

                if (proc == null)
                {
                    MessageBox.Show(
                        "No se pudo crear el proceso para LabVision.",
                        "LabVision - Error al Iniciar",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                    return;
                }

                // Monitorear los primeros segundos para detectar fallas tempranas
                // Si el proceso termina rápidamente (<= 2500 ms) con código de error, alertar
                bool exitedEarly = proc.WaitForExit(2500);
                if (exitedEarly && proc.ExitCode != 0)
                {
                    string errorMessage = "";
                    try
                    {
                        // Ejecutar brevemente en modo diagnóstico para capturar el traceback
                        string diagPython = pythonPath;
                        if (diagPython.EndsWith("pythonw.exe", StringComparison.OrdinalIgnoreCase))
                        {
                            string candidatePy = diagPython.Substring(0, diagPython.Length - 5) + ".exe";
                            if (File.Exists(candidatePy))
                            {
                                diagPython = candidatePy;
                            }
                        }

                        ProcessStartInfo diagPsi = new ProcessStartInfo();
                        diagPsi.FileName = diagPython;
                        diagPsi.Arguments = "\"" + appPy + "\"";
                        diagPsi.WorkingDirectory = baseDir;
                        diagPsi.UseShellExecute = false;
                        diagPsi.CreateNoWindow = true;
                        diagPsi.RedirectStandardError = true;
                        diagPsi.RedirectStandardOutput = true;
                        if (Directory.Exists(runtimeDir))
                        {
                            diagPsi.EnvironmentVariables["PYTHONHOME"] = runtimeDir;
                            string currentPath = Environment.GetEnvironmentVariable("PATH") ?? "";
                            diagPsi.EnvironmentVariables["PATH"] = runtimeDir + ";" + Path.Combine(runtimeDir, "Scripts") + ";" + currentPath;
                        }
                        diagPsi.EnvironmentVariables["PYTHONPATH"] = baseDir;

                        using (Process diagProc = Process.Start(diagPsi))
                        {
                            if (diagProc != null)
                            {
                                string stdErr = diagProc.StandardError.ReadToEnd();
                                diagProc.WaitForExit(3500);
                                if (!string.IsNullOrEmpty(stdErr))
                                {
                                    errorMessage = stdErr.Trim();
                                }
                            }
                        }
                    }
                    catch
                    {
                        // Fallback silencioso si el intento diagnóstico no logra ejecutarse
                    }

                    string msg = string.Format("LabVision se cerró de manera prematura con código de salida {0}.", proc.ExitCode);
                    if (!string.IsNullOrEmpty(errorMessage))
                    {
                        if (errorMessage.Length > 1000)
                        {
                            errorMessage = errorMessage.Substring(0, 1000) + "\n... [truncado]";
                        }
                        msg += "\n\nDetalles del error detectado:\n" + errorMessage;
                    }
                    else
                    {
                        msg += "\n\nEs posible que falten dependencias o bibliotecas en el entorno de Python.";
                    }

                    MessageBox.Show(
                        msg,
                        "LabVision - Error de Inicialización",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Error inesperado al ejecutar LabVision:\n" + ex.Message,
                    "LabVision - Excepción",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }
    }
}