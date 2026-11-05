import os
import shutil

class ResourceManager:
    def get_system_metrics(self):
        disk = shutil.disk_usage(".")
        free_ram = total_ram = 0
        try:
            with open("/proc/meminfo", encoding="ascii") as stream:
                for line in stream:
                    if line.startswith("MemTotal:"):
                        total_ram = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        free_ram = int(line.split()[1]) // 1024
        except OSError:
            pass
        return {"total_ram_mb": total_ram, "free_ram_mb": free_ram,
                "free_disk_gb": round(disk.free / (1024 ** 3), 2)}

    def recommend_engine(self):
        # L3 is the only currently implemented native inference engine.
        return "L3"
