using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;

namespace LabVisionLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string appPy = Path.Combine(baseDir, "app.py");

                if (!File.Exists(appPy))
                {
                    // Fallback a E:\reotaxis si se ejecuta desde otro directorio
                    if (File.Exists(@"E:\reotaxis\app.py"))
                    {
                        baseDir = @"E:\reotaxis";
                        appPy = @"E:\reotaxis\app.py";
                    }
                    else
                    {
                        MessageBox.Show("No se encontró el archivo principal 'app.py' en:\n" + baseDir,
                            "LabVision - Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        return;
                    }
                }

                string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

                string[] candidates = new string[]
                {
                    @"C:\Users\farin\.venv\Scripts\pythonw.exe",
                    Path.Combine(userProfile, @".venv\Scripts\pythonw.exe"),
                    Path.Combine(baseDir, @".venv\Scripts\pythonw.exe"),
                    Path.Combine(localAppData, @"Programs\Python\Python312\pythonw.exe"),
                    Path.Combine(localAppData, @"Programs\Python\Python311\pythonw.exe"),
                    Path.Combine(localAppData, @"Programs\Python\Python310\pythonw.exe"),
                    @"C:\Python312\pythonw.exe",
                    @"C:\Python311\pythonw.exe",
                    @"C:\Python310\pythonw.exe",
                    @"C:\Program Files\Python312\pythonw.exe",
                    @"C:\Program Files\Python311\pythonw.exe",
                    @"C:\Users\farin\.venv\Scripts\python.exe",
                    Path.Combine(userProfile, @".venv\Scripts\python.exe")
                };

                string pythonPath = null;
                foreach (string c in candidates)
                {
                    if (File.Exists(c))
                    {
                        pythonPath = c;
                        break;
                    }
                }

                // Si no se encuentra en rutas conocidas, buscar en PATH
                if (string.IsNullOrEmpty(pythonPath))
                {
                    string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
                    foreach (string p in pathEnv.Split(';'))
                    {
                        string trimmed = p.Trim();
                        if (string.IsNullOrEmpty(trimmed)) continue;
                        string target = Path.Combine(trimmed, "pythonw.exe");
                        if (File.Exists(target))
                        {
                            pythonPath = target;
                            break;
                        }
                    }
                }

                if (string.IsNullOrEmpty(pythonPath))
                {
                    DialogResult res = MessageBox.Show(
                        "LabVision requiere Python 3.10+ configurado en el sistema.\n\n" +
                        "¿Desea ejecutar el instalador automatizado ahora?",
                        "LabVision - Instalación requerida",
                        MessageBoxButtons.YesNo,
                        MessageBoxIcon.Question);

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
                    }
                    return;
                }

                // Iniciar de forma 100% silenciosa sin ventana de consola negra
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonPath;
                psi.Arguments = "\"" + appPy + "\"";
                psi.WorkingDirectory = baseDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error al iniciar LabVision:\n" + ex.Message,
                    "LabVision", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
