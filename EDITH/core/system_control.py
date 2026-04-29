"""
System Control Skills for EDITH-AI

Provides:
  - System Info       : detailed PC hardware/OS info
  - Power Manager     : shutdown / restart / sleep (with confirmation)
  - Volume Control    : set / up / down / mute / unmute
  - Brightness Control: set / up / down
  - Virus Scan        : trigger platform AV scan
  - Webcam Control    : enable / disable
  - Mouse Speed       : adjust pointer speed
  - Keyboard Lights   : set RGB via openrgb / ckb-next
  - Time Sync         : sync clock with NTP
  - Calendar View     : display current month calendar
  - Notifications     : enable / disable Do Not Disturb
  - Task Manager      : open monitor or kill a process (kill with confirmation)
  - Auto Update       : trigger OS package-manager updates
"""

import calendar as _calendar_mod
import datetime
import os
import platform
import subprocess
import re
from typing import Dict, Optional, Union

import psutil


class SystemControl:
    """Handles all System Control commands."""

    def __init__(self, config=None):
        self.config = config
        self._sys = platform.system().lower()

    # ------------------------------------------------------------------
    # Public entry point  (synchronous – no LLM needed)
    # ------------------------------------------------------------------

    def handle(self, text: str) -> Optional[Union[str, Dict]]:
        """
        Return:
          - str            → direct reply
          - dict           → confirmation required  {"requires_confirmation", "message", "pending_action"}
          - None           → not handled here
        """
        raw = (text or "").strip()
        low = raw.lower()

        # --- System Info ---
        if low in {
            "system info", "pc info", "computer info", "pc details",
            "system details", "about this pc", "show system info",
        }:
            return self._system_info()

        # --- Power Manager ---
        if low in {"shutdown", "shut down", "power off", "turn off pc", "shutdown pc"}:
            return self._confirm("shutdown", "Shut down the computer?")

        if low in {"restart", "reboot", "restart pc", "reboot pc"}:
            return self._confirm("restart", "Restart the computer?")

        if low in {"sleep", "sleep mode", "sleep pc", "put to sleep"}:
            return self._confirm("sleep", "Put the computer to sleep?")

        # --- Volume Control ---
        m = re.match(r"^(?:set volume|volume set|volume)\s+(\d+)\s*%?$", low)
        if m:
            return self._set_volume(int(m.group(1)))

        if low in {"volume up", "increase volume", "louder", "turn up volume"}:
            return self._volume_change(+10)

        if low in {"volume down", "decrease volume", "quieter", "turn down volume"}:
            return self._volume_change(-10)

        if low in {"mute volume", "mute audio", "mute sound", "mute"}:
            return self._mute_audio(True)

        if low in {"unmute volume", "unmute audio", "unmute sound", "unmute"}:
            return self._mute_audio(False)

        # --- Brightness Control ---
        m = re.match(r"^(?:set brightness|brightness set|brightness)\s+(\d+)\s*%?$", low)
        if m:
            return self._set_brightness(int(m.group(1)))

        if low in {"brightness up", "increase brightness", "brighter"}:
            return self._brightness_delta(+10)

        if low in {"brightness down", "decrease brightness", "dimmer"}:
            return self._brightness_delta(-10)

        # --- Virus Scan ---
        if low in {
            "virus scan", "run virus scan", "scan for viruses",
            "malware scan", "antivirus scan",
        }:
            return self._virus_scan()

        # --- Webcam Control ---
        if low in {"webcam on", "enable webcam", "turn on webcam"}:
            return self._webcam_control(True)

        if low in {"webcam off", "disable webcam", "turn off webcam"}:
            return self._webcam_control(False)

        # --- Mouse Speed ---
        m = re.match(r"^(?:set mouse speed|mouse speed)\s+(\d+)$", low)
        if m:
            return self._set_mouse_speed(int(m.group(1)))

        # --- Keyboard Lights ---
        m = re.match(r"^(?:keyboard lights?|keyboard colou?r)\s+(.+)$", low)
        if m:
            return self._keyboard_lights(m.group(1).strip())

        # --- Time Sync ---
        if low in {"sync time", "sync system time", "time sync", "update time", "synchronize time"}:
            return self._sync_time()

        # --- Calendar View ---
        if low in {
            "show calendar", "calendar", "calendar view",
            "view calendar", "show month", "show this month",
        }:
            return self._show_calendar()

        # --- Notifications ---
        if low in {"notifications on", "enable notifications", "turn on notifications"}:
            return self._notifications(True)

        if low in {
            "notifications off", "disable notifications",
            "turn off notifications", "do not disturb", "dnd on",
        }:
            return self._notifications(False)

        # --- Task Manager ---
        if low in {"task manager", "open task manager", "show task manager"}:
            return self._open_task_manager()

        m = re.match(r"^(?:kill process|kill app|close app|stop process|force quit)\s+(.+)$", raw, re.IGNORECASE)
        if m:
            proc_name = m.group(1).strip()
            return self._confirm(
                "kill_process",
                f"Kill process '{proc_name}'?",
                target=proc_name,
            )

        # list running processes
        if low in {"list processes", "show processes", "running processes"}:
            return self._list_processes()

        # --- Auto Update ---
        if low in {"auto update", "update pc", "update system", "update software", "run updates"}:
            return self._auto_update()

        return None

    # ------------------------------------------------------------------
    # Called by CommandRouter.execute_pending after user confirms
    # ------------------------------------------------------------------

    def execute_pending(self, action: str, target: str = "") -> str:
        if action == "shutdown":
            return self._power_action("shutdown")
        if action == "restart":
            return self._power_action("restart")
        if action == "sleep":
            return self._power_action("sleep")
        if action == "kill_process":
            return self._kill_process(target)
        return "Unknown system control action."

    # ------------------------------------------------------------------
    # System Info
    # ------------------------------------------------------------------

    def _system_info(self) -> str:
        vm = psutil.virtual_memory()
        du = psutil.disk_usage("/")
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        batt = psutil.sensors_battery()

        lines = [
            f"OS         : {platform.system()} {platform.release()} ({platform.version()})",
            f"Machine    : {platform.machine()} | Node: {platform.node()}",
            f"Processor  : {platform.processor() or 'N/A'}",
            f"CPU cores  : {cpu_count} | Usage: {psutil.cpu_percent(interval=1):.1f}%",
        ]
        if cpu_freq:
            lines.append(
                f"CPU freq   : {cpu_freq.current:.0f} MHz"
                + (f" (max {cpu_freq.max:.0f} MHz)" if cpu_freq.max else "")
            )
        lines += [
            f"RAM        : {vm.used / 1024**3:.1f} GB / {vm.total / 1024**3:.1f} GB ({vm.percent}%)",
            f"Disk (/)   : {du.used / 1024**3:.1f} GB / {du.total / 1024**3:.1f} GB ({du.percent}%)",
        ]
        if batt:
            status = "charging" if batt.power_plugged else "discharging"
            lines.append(f"Battery    : {batt.percent:.0f}% ({status})")
        else:
            lines.append("Battery    : N/A")
        lines.append(f"Python     : {platform.python_version()}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Power Manager
    # ------------------------------------------------------------------

    def _power_action(self, action: str) -> str:
        sys = self._sys
        try:
            if action == "shutdown":
                if sys.startswith("win"):
                    subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
                else:
                    subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
                return "Shutting down…"

            if action == "restart":
                if sys.startswith("win"):
                    subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
                else:
                    subprocess.run(["sudo", "shutdown", "-r", "now"], check=True)
                return "Restarting…"

            if action == "sleep":
                if sys.startswith("win"):
                    subprocess.run(
                        ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                        check=True,
                    )
                elif sys == "darwin":
                    subprocess.run(["pmset", "sleepnow"], check=True)
                else:
                    subprocess.run(["systemctl", "suspend"], check=True)
                return "Going to sleep…"

        except Exception as e:
            return f"Power action failed: {e}"
        return "Done."

    # ------------------------------------------------------------------
    # Volume Control
    # ------------------------------------------------------------------

    def _set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        sys = self._sys
        try:
            if sys == "darwin":
                subprocess.run(
                    ["osascript", "-e", f"set volume output volume {level}"],
                    check=True, timeout=5,
                )
                return f"Volume set to {level}%."
            if sys.startswith("linux"):
                subprocess.run(
                    ["amixer", "-q", "sset", "Master", f"{level}%"],
                    check=True, timeout=5,
                )
                return f"Volume set to {level}%."
            # Windows – try nircmd (if installed)
            r = subprocess.run(
                ["nircmd", "setsysvolume", str(int(level * 655.35))],
                capture_output=True, timeout=5,
            )
            if r.returncode == 0:
                return f"Volume set to {level}%."
        except Exception:
            pass
        return f"Volume set to {level}% (use your keyboard shortcut to confirm on this OS)."

    def _volume_change(self, delta: int) -> str:
        direction = "increased" if delta > 0 else "decreased"
        sys = self._sys
        try:
            if sys == "darwin":
                expr = (
                    f"set volume output volume "
                    f"(output volume of (get volume settings) {'+' if delta > 0 else '-'} {abs(delta)})"
                )
                subprocess.run(["osascript", "-e", expr], check=True, timeout=5)
                return f"Volume {direction}."
            if sys.startswith("linux"):
                arg = f"{abs(delta)}%{'+' if delta > 0 else '-'}"
                subprocess.run(
                    ["amixer", "-q", "sset", "Master", arg],
                    check=True, timeout=5,
                )
                return f"Volume {direction}."
        except Exception:
            pass
        return f"Volume {direction} (keyboard shortcut may be needed on Windows)."

    def _mute_audio(self, mute: bool) -> str:
        action = "muted" if mute else "unmuted"
        sys = self._sys
        try:
            if sys == "darwin":
                val = "true" if mute else "false"
                subprocess.run(
                    ["osascript", "-e", f"set volume output muted {val}"],
                    check=True, timeout=5,
                )
                return f"Audio {action}."
            if sys.startswith("linux"):
                toggle = "mute" if mute else "unmute"
                subprocess.run(
                    ["amixer", "-q", "sset", "Master", toggle],
                    check=True, timeout=5,
                )
                return f"Audio {action}."
        except Exception:
            pass
        return f"Audio {action} (use your keyboard shortcut on Windows)."

    # ------------------------------------------------------------------
    # Brightness Control
    # ------------------------------------------------------------------

    def _set_brightness(self, level: int) -> str:
        level = max(0, min(100, level))
        sys = self._sys
        try:
            if sys.startswith("win"):
                script = (
                    f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                    f".WmiSetBrightness(1,{level})"
                )
                r = subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0:
                    return f"Brightness set to {level}%."
                return f"Brightness change failed: {r.stderr.strip()}"

            if sys == "darwin":
                subprocess.run(
                    ["osascript", "-e",
                     f'tell application "System Events" to set brightness to {level / 100:.2f}'],
                    check=True, timeout=5,
                )
                return f"Brightness set to {level}%."

            # Linux – try brightnessctl then xrandr
            for cmd in (
                ["brightnessctl", "set", f"{level}%"],
                ["xrandr", "--output", "eDP-1", "--brightness", f"{level / 100:.2f}"],
            ):
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if r.returncode == 0:
                        return f"Brightness set to {level}%."
                except FileNotFoundError:
                    continue

        except Exception as e:
            return f"Brightness control failed: {e}"
        return f"Could not set brightness to {level}% on this system."

    def _brightness_delta(self, delta: int) -> str:
        direction = "increased" if delta > 0 else "decreased"
        try:
            if self._sys.startswith("linux"):
                arg = f"{abs(delta)}%{'+' if delta > 0 else '-'}"
                subprocess.run(["brightnessctl", "set", arg], check=True, timeout=10)
                return f"Brightness {direction}."
        except Exception:
            pass
        return f"Brightness {direction} (keyboard shortcut may be needed)."

    # ------------------------------------------------------------------
    # Virus Scan
    # ------------------------------------------------------------------

    def _virus_scan(self) -> str:
        sys = self._sys
        try:
            if sys.startswith("win"):
                r = subprocess.run(
                    ["powershell", "-Command", "Start-MpScan -ScanType QuickScan"],
                    capture_output=True, text=True, timeout=15,
                )
                if r.returncode == 0:
                    return "Windows Defender quick scan started."
                return f"Scan failed: {r.stderr.strip()}"

            if sys == "darwin":
                subprocess.Popen(["open", "-a", "Malwarebytes"])
                return "Opened Malwarebytes (if installed). No built-in CLI scanner on macOS."

            # Linux – try clamscan
            for scanner_cmd in (
                ["clamscan", "--quiet", "--recursive", os.path.expanduser("~")],
            ):
                try:
                    subprocess.Popen(scanner_cmd)
                    return "ClamAV scan started in the background."
                except FileNotFoundError:
                    pass
            return "No scanner found. Install ClamAV: sudo apt install clamav"

        except Exception as e:
            return f"Virus scan error: {e}"

    # ------------------------------------------------------------------
    # Webcam Control
    # ------------------------------------------------------------------

    def _webcam_control(self, enable: bool) -> str:
        action = "enabled" if enable else "disabled"
        sys = self._sys
        try:
            if sys.startswith("win"):
                state = "Enable" if enable else "Disable"
                r = subprocess.run(
                    ["powershell", "-Command",
                     f'Get-PnpDevice -Class Camera | {state}-PnpDevice -Confirm:$false'],
                    capture_output=True, text=True, timeout=15,
                )
                if r.returncode == 0:
                    return f"Webcam {action}."
                return f"Webcam {action} failed: {r.stderr.strip() or 'permission denied'}"

            if sys.startswith("linux"):
                mod = "rmmod" if not enable else "modprobe"
                r = subprocess.run(
                    ["sudo", mod, "uvcvideo"],
                    capture_output=True, text=True, timeout=10,
                )
                return f"Webcam {action}." if r.returncode == 0 else f"Webcam {action} failed: {r.stderr.strip()}"

        except Exception as e:
            return f"Webcam control failed: {e}"
        return f"Webcam control not supported on {platform.system()}."

    # ------------------------------------------------------------------
    # Mouse Speed
    # ------------------------------------------------------------------

    def _set_mouse_speed(self, speed: int) -> str:
        speed = max(1, min(20, speed))
        sys = self._sys
        try:
            if sys.startswith("win"):
                r = subprocess.run(
                    ["powershell", "-Command",
                     f"Set-ItemProperty -Path 'HKCU:\\Control Panel\\Mouse' "
                     f"-Name MouseSensitivity -Value {speed}"],
                    capture_output=True, text=True, timeout=10,
                )
                return f"Mouse speed set to {speed}." if r.returncode == 0 else f"Mouse speed change failed."

            if sys == "darwin":
                r = subprocess.run(
                    ["defaults", "write", "-g", "com.apple.mouse.scaling", str(speed / 10)],
                    capture_output=True, text=True, timeout=10,
                )
                return f"Mouse speed set to {speed}." if r.returncode == 0 else "Mouse speed change failed."

            if sys.startswith("linux"):
                # xinput accel range is -1 to 1; map speed 1-20 → approx -0.95 to +0.95
                accel = round((speed - 10.5) / 10, 2)
                r = subprocess.run(
                    ["xinput", "--set-prop", "Virtual core pointer",
                     "libinput Accel Speed", str(accel)],
                    capture_output=True, text=True, timeout=10,
                )
                return f"Mouse speed set to {speed}." if r.returncode == 0 else f"Mouse speed failed: {r.stderr.strip()}"

        except Exception as e:
            return f"Mouse speed control failed: {e}"
        return "Mouse speed change not supported on this OS."

    # ------------------------------------------------------------------
    # Keyboard Lights
    # ------------------------------------------------------------------

    def _keyboard_lights(self, color: str) -> str:
        # Try OpenRGB first, then ckb-next
        for cmd in (
            ["openrgb", "--color", color],
            ["ckb-next", "-c", color],
        ):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    return f"Keyboard lights set to {color}."
            except FileNotFoundError:
                continue
            except Exception:
                continue
        return (
            f"Could not set keyboard lights to '{color}'.\n"
            "Install OpenRGB (https://openrgb.org) for RGB keyboard control."
        )

    # ------------------------------------------------------------------
    # Time Sync
    # ------------------------------------------------------------------

    def _sync_time(self) -> str:
        sys = self._sys
        try:
            if sys.startswith("win"):
                r = subprocess.run(
                    ["w32tm", "/resync", "/force"],
                    capture_output=True, text=True, timeout=15,
                )
                out = (r.stdout + r.stderr).strip()
                return f"Time sync: {out}" if out else "Time synced."

            if sys == "darwin":
                r = subprocess.run(
                    ["sudo", "sntp", "-sS", "time.apple.com"],
                    capture_output=True, text=True, timeout=15,
                )
                return "Time synced with Apple time server." if r.returncode == 0 else f"Sync failed: {r.stderr.strip()}"

            # Linux
            for cmd in (
                ["sudo", "timedatectl", "set-ntp", "true"],
                ["sudo", "ntpdate", "-u", "pool.ntp.org"],
            ):
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    if r.returncode == 0:
                        return "System time synced."
                except FileNotFoundError:
                    continue
            return "Time sync failed. Install ntp: sudo apt install ntp"

        except Exception as e:
            return f"Time sync failed: {e}"

    # ------------------------------------------------------------------
    # Calendar View
    # ------------------------------------------------------------------

    def _show_calendar(self) -> str:
        now = datetime.datetime.now()
        try:
            cal = _calendar_mod.month(now.year, now.month)
            return f"Calendar – {now.strftime('%B %Y')}:\n{cal}"
        except Exception as e:
            return f"Calendar error: {e}"

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _notifications(self, enable: bool) -> str:
        action = "on" if enable else "off"
        sys = self._sys
        try:
            if sys.startswith("win"):
                val = 0 if enable else 1
                r = subprocess.run(
                    ["powershell", "-Command",
                     f"Set-ItemProperty -Path "
                     f"'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\PushNotifications' "
                     f"-Name ToastEnabled -Value {val}"],
                    capture_output=True, text=True, timeout=10,
                )
                return f"Notifications turned {action}." if r.returncode == 0 else "Notification change failed."

            if sys == "darwin":
                # doNotDisturb=true means DND on (notifications suppressed)
                # doNotDisturb=false means DND off (notifications enabled)
                bool_val = "false" if enable else "true"
                r = subprocess.run(
                    ["defaults", "-currentHost", "write",
                     "com.apple.notificationcenterui", "doNotDisturb",
                     "-bool", bool_val],
                    capture_output=True, text=True, timeout=10,
                )
                label = "Do Not Disturb enabled." if not enable else "Notifications enabled."
                return label if r.returncode == 0 else "Could not change notification settings."

        except Exception as e:
            return f"Notification control failed: {e}"
        return "Notification control not fully supported on this platform."

    # ------------------------------------------------------------------
    # Task Manager
    # ------------------------------------------------------------------

    def _open_task_manager(self) -> str:
        sys = self._sys
        try:
            if sys.startswith("win"):
                subprocess.Popen(["taskmgr"])
                return "Opened Task Manager."
            if sys == "darwin":
                subprocess.Popen(["open", "-a", "Activity Monitor"])
                return "Opened Activity Monitor."
            # Linux – try common GUIs, fall back to htop in terminal
            for tm in ["gnome-system-monitor", "ksysguard", "lxtask"]:
                try:
                    subprocess.Popen([tm])
                    return f"Opened {tm}."
                except FileNotFoundError:
                    continue
            subprocess.Popen(["x-terminal-emulator", "-e", "htop"])
            return "Opened htop in terminal."
        except Exception as e:
            return f"Task manager error: {e}"

    def _list_processes(self) -> str:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        lines = ["Top processes by CPU:"]
        for p in procs[:15]:
            lines.append(
                f"  {p['name']:<28} PID {p['pid']:>6}  "
                f"CPU {p['cpu_percent']:>5.1f}%  "
                f"MEM {p['memory_percent']:>5.1f}%"
            )
        return "\n".join(lines)

    def _kill_process(self, name: str) -> str:
        killed = []
        # First pass: exact name match (case-insensitive)
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name.lower() == (proc.info["name"] or "").lower():
                    proc.terminate()
                    killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Second pass: substring match only if no exact match found
        if not killed:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if name.lower() in (proc.info["name"] or "").lower():
                        proc.terminate()
                        killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if killed:
            return f"Terminated: {', '.join(killed)}"
        return f"No process matching '{name}' found."

    # ------------------------------------------------------------------
    # Auto Update
    # ------------------------------------------------------------------

    def _auto_update(self) -> str:
        sys = self._sys
        try:
            if sys.startswith("win"):
                r = subprocess.run(
                    ["powershell", "-Command",
                     "(New-Object -ComObject Microsoft.Update.AutoUpdate).DetectNow()"],
                    capture_output=True, text=True, timeout=15,
                )
                return "Windows Update check started." if r.returncode == 0 else f"Update failed: {r.stderr.strip()}"

            if sys == "darwin":
                r = subprocess.run(
                    ["softwareupdate", "-l"],
                    capture_output=True, text=True, timeout=60,
                )
                return (r.stdout + r.stderr).strip() or "No software updates available."

            # Linux – try common package managers
            for mgr, cmd in [
                ("apt",    ["sudo", "apt", "update"]),
                ("dnf",    ["sudo", "dnf", "check-update"]),
                ("pacman", ["sudo", "pacman", "-Sy", "--noconfirm"]),
                ("snap",   ["sudo", "snap", "refresh"]),
            ]:
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    out = (r.stdout + r.stderr).strip()
                    return out[:2000] if out else f"Update via {mgr} complete."
                except FileNotFoundError:
                    continue
            return "No supported package manager found for auto-update."

        except Exception as e:
            return f"Auto update failed: {e}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _confirm(action: str, question: str, target: str = "") -> Dict:
        """Build a confirmation dict compatible with CommandRouter."""
        return {
            "requires_confirmation": True,
            "message": f"{question} (yes/no)",
            "pending_action": {
                "type": "system_control",
                "action": action,
                "target": target,
            },
        }
