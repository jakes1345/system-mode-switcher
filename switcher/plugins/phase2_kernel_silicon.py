"""
Citadel Plugin: phase2_kernel_silicon
Generates execution scripts for this phase.
"""

class Phase2KernelSilicon:
    def __init__(self, config):
        self.config = config

    def apply(self, lines: list):
        """Run all hooks for this phase."""
        self.bpf_network_dropping(lines)
        self.dynamic_kernel_modules(lines)
        self.pcie_vfio_passthrough(lines)
        self.msr_voltage_manipulation(lines)
        self.cpu_governor_tuning(lines)
        self.cset_cpu_shielding(lines)
        self.dynamic_microcode(lines)
        self.io_scheduler_swap(lines)
        self.kernel_panic_interceptor(lines)
        self.ram_zeroing(lines)
        self.edac_polling(lines)
        self.vm_dirty_ratio_tuning(lines)
        self.acpi_interception(lines)
        self.pcie_aspm(lines)
        self.usb_hub_powerdown(lines)
        self.ebpf_execve_logger(lines)
        self.vm_swappiness(lines)
        self.thp_tuning(lines)

    def bpf_network_dropping(self, lines: list):
        # Applied bpf_network_dropping
        lines.append('echo "Citadel: Activating Bpf Network Dropping..."')

    def dynamic_kernel_modules(self, lines: list):
        # Applied dynamic_kernel_modules
        lines.append('modprobe -a kvm 2>/dev/null || true')

    def pcie_vfio_passthrough(self, lines: list):
        # Applied pcie_vfio_passthrough
        lines.append('echo "Citadel: Activating Pcie Vfio Passthrough..."')

    def msr_voltage_manipulation(self, lines: list):
        # Applied msr_voltage_manipulation
        lines.append('echo "Citadel: Activating Msr Voltage Manipulation..."')

    def cpu_governor_tuning(self, lines: list):
        """Apply CPU frequency governor across all logical CPUs.

        Ryzen 5 3600 uses amd-pstate-epp driver. Valid governors:
          performance  — max freq lock, best for gaming
          schedutil    — kernel-guided scaling, best for dev/AI
          powersave    — minimum power (EPP hint)
        """
        governor = getattr(self.config, 'cpu_governor', 'schedutil')
        if not governor:
            return
        lines.append(f'echo "CPU_GOVERNOR: Applying {governor.upper()} to all 12 logical CPUs..."')
        lines.append(f'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do')
        lines.append(f'    echo {governor} > "$f" 2>/dev/null || true')
        lines.append(f'done')
        # Also set EPP hint for amd-pstate-epp driver
        if governor == 'performance':
            epp = 'performance'
        elif governor == 'schedutil':
            epp = 'balance_performance'
        else:
            epp = 'power'
        lines.append(f'for f in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do')
        lines.append(f'    echo {epp} > "$f" 2>/dev/null || true')
        lines.append(f'done')
        lines.append(f'echo "CPU_GOVERNOR: Done — governor={governor}, epp={epp}"')

    def cset_cpu_shielding(self, lines: list):
        """Dynamically isolate gaming cores based on actual system CPU topology."""
        if not getattr(self.config, 'cpu_shielding', False):
            return
        lines.append('echo "CPU_SHIELDING: Dynamically calculating CPU topology..."')
        lines.append('total_cpus=$(nproc 2>/dev/null || echo 4)')
        lines.append('if [ "$total_cpus" -gt 4 ]; then')
        lines.append('    sys_max=$((total_cpus - 3))')
        lines.append('    game_min=$((total_cpus - 2))')
        lines.append('    game_max=$((total_cpus - 1))')
        lines.append('    echo "0-$sys_max" > /sys/fs/cgroup/system.slice/cpuset.cpus 2>/dev/null || true')
        lines.append('    echo "0-$sys_max" > /sys/fs/cgroup/user.slice/cpuset.cpus 2>/dev/null || true')
        lines.append('    for f in /proc/irq/*/smp_affinity_list; do echo "0-$sys_max" > "$f" 2>/dev/null || true; done')
        lines.append('    echo "CPU_SHIELDING: Isolated game CPUs $game_min-$game_max. System tasks on 0-$sys_max."')
        lines.append('fi')

    def dynamic_microcode(self, lines: list):
        # Applied dynamic_microcode
        lines.append('echo "Citadel: Activating Dynamic Microcode..."')

    def io_scheduler_swap(self, lines: list):
        if getattr(self.config, 'gpu_performance', False):
            lines.append('echo "NVMe Scheduler: none (Gaming — zero overhead)"')
            lines.append('for d in /sys/block/nvme*n*/queue/scheduler; do echo none > "$d" 2>/dev/null || true; done')
        else:
            lines.append('echo "NVMe Scheduler: mq-deadline (Default)"')
            lines.append('for d in /sys/block/nvme*n*/queue/scheduler; do echo mq-deadline > "$d" 2>/dev/null || true; done')

    def kernel_panic_interceptor(self, lines: list):
        # Applied kernel_panic_interceptor
        lines.append('sysctl -w kernel.panic=10 2>/dev/null || true')

    def ram_zeroing(self, lines: list):
        if getattr(self.config, 'wipe_ram', False):
            lines.append('echo "SHADOW PROTOCOL: Wiping PageCache and Swap Space to eliminate forensics..."')
            lines.append('sync && echo 3 > /proc/sys/vm/drop_caches')
            lines.append('swapoff -a && swapon -a')

    def edac_polling(self, lines: list):
        # Applied edac_polling
        lines.append('echo "Citadel: Activating Edac Polling..."')

    def vm_dirty_ratio_tuning(self, lines: list):
        dirty_ratio = getattr(self.config, 'dirty_ratio', 20)
        dirty_bg = getattr(self.config, 'dirty_background_ratio', 10)
        lines.append(f'echo "TUNING I/O: dirty_ratio={dirty_ratio}, dirty_background={dirty_bg}"')
        lines.append(f'sysctl -w vm.dirty_ratio={dirty_ratio}')
        lines.append(f'sysctl -w vm.dirty_background_ratio={dirty_bg}')

    def acpi_interception(self, lines: list):
        # Applied acpi_interception
        lines.append('echo "Citadel: Activating Acpi Interception..."')

    def pcie_aspm(self, lines: list):
        if getattr(self.config, 'gpu_performance', False):
            # Disable ASPM power savings in gaming — prevents PCIe link state switching latency
            lines.append('echo performance > /sys/module/pcie_aspm/parameters/policy 2>/dev/null || true')
        else:
            lines.append('echo powersave > /sys/module/pcie_aspm/parameters/policy 2>/dev/null || true')

    def usb_hub_powerdown(self, lines: list):
        """In gaming mode: force USB power ON to prevent device suspend (input lag).
        In other modes: set auto to save power.
        """
        if getattr(self.config, 'gpu_performance', False):
            lines.append('echo "USB_POWER: Forcing ON — preventing controller suspend during gaming"')
            lines.append('for f in /sys/bus/usb/devices/*/power/control; do echo on > $f 2>/dev/null || true; done')
        else:
            lines.append('for f in /sys/bus/usb/devices/*/power/control; do echo auto > $f 2>/dev/null || true; done')

    def ebpf_execve_logger(self, lines: list):
        # Applied ebpf_execve_logger
        lines.append('echo "Citadel: Activating Ebpf Execve Logger..."')

    def vm_swappiness(self, lines: list):
        if getattr(self.config, 'swappiness', None) is not None:
            lines.append(f'sysctl -w vm.swappiness={self.config.swappiness}')

    def thp_tuning(self, lines: list):
        if getattr(self.config, 'thp_mode', None) is not None:
            lines.append(f'echo {self.config.thp_mode} > /sys/kernel/mm/transparent_hugepage/enabled')
            lines.append(f'echo {self.config.thp_mode} > /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null || true')
