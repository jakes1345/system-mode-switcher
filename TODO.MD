# Obsidian Citadel (PhazeOS Core) - Master Architecture Roadmap

This document serves as the absolute master blueprint for evolving the Obsidian Citadel Orchestrator into the foundational nervous system of a custom Linux Operating System.

## Phase 1: Bootloader & Init System (The Genesis Layer)
1. [ ] Rewrite initramfs generation to include Citadel hooks before pivot_root.
2. [ ] Integrate with systemd-boot or GRUB to dynamically select boot profiles via GRUB env vars.
3. [ ] Build an Early-Boot Splash screen (Plymouth theme) that displays Citadel initialization phases.
4. [ ] Move Citadel from `multi-user.target` to a highly prioritized `sysinit.target` service.
5. [ ] Implement a Citadel Secure Boot signature verification layer for kernel modules.
6. [ ] Create a `citadel.target` in systemd that replaces `graphical.target` for headless gaming mode.
7. [ ] Build an emergency physical panic-button hook (SysRq interception) to instant-drop to rescue shell.
8. [ ] Implement LUKS decryption unlocking via an encrypted USB hardware key (YubiKey integration).
9. [ ] Create a custom boot parameter parser (`citadel.mode=gaming`) to set profile at the kernel cmdline.
10. [ ] Optimize systemd parallelization to achieve sub-2-second boot times to the Citadel daemon.

## Phase 2: Kernel & Silicon Manipulation
11. [ ] Implement BPF/XDP programs for raw network packet dropping at the NIC firmware level.
12. [ ] Add real-time dynamic kernel module loading/unloading (rmmod/insmod) per profile.
13. [ ] Implement PCIe VFIO-PCI passthrough unbinding for secondary GPUs on the fly.
14. [ ] Build a custom MSR (Model-Specific Register) wrapper in C to manipulate CPU voltages (Undervolting).
15. [ ] Integrate `cset` (cpuset) dynamic CPU shielding to physically partition OS background tasks away from Cores 2-15.
16. [ ] Add support for dynamically loading optimized CPU microcode on boot.
17. [ ] Implement I/O scheduler swapping (mq-deadline vs kyber) based on the active storage profile.
18. [ ] Build a kernel panic interceptor that logs stack traces directly to a Citadel SQLite database.
19. [ ] Implement a RAM clearing/zeroing feature for Red Team mode to wipe sensitive data on exit.
20. [ ] Add native EDAC (Error Detection and Correction) polling for ECC memory servers.
21. [ ] Tune VM dirty_ratio and dirty_background_ratio on the fly for heavy database (AI) vs low-latency (Gaming) workloads.
22. [ ] Intercept ACPI events (lid close, power button) entirely inside Citadel, bypassing systemd-logind.
23. [ ] Implement dynamic PCIe link state power management (ASPM) toggling for laptops.
24. [ ] Add custom sysfs rules to completely power down unmapped USB hubs.
25. [ ] Build a kernel tracepoint logger using eBPF to monitor all `execve` syscalls for stealth mode.

## Phase 3: Filesystem & Storage (The ZFS/BTRFS Era)
26. [ ] Migrate the base OS from ext4 to a BTRFS/ZFS root dataset.
27. [ ] Implement Zero-Cost ZFS Snapshots triggered instantly on Citadel profile changes.
28. [ ] Build a "Kamikaze Mode" that instantly formats the LUKS header and shreds the RAM.
29. [ ] Create overlayfs ephemeral root filesystems (Live OS mode) for untrusted browsing sessions.
30. [ ] Build a Citadel background daemon to scrub ZFS pools during idle CPU hours.
31. [ ] Implement tiered storage caching (bcache/LVM cache) prioritizing games to NVMe.
32. [ ] Integrate automatic deduplication toggling for specific `/var/lib/docker` datasets.
33. [ ] Build a file integrity monitoring system (FIM) using inotify for the `/boot` and `/etc` directories.
34. [ ] Create a custom `/dev/shm` dynamic resizing algorithm based on the active profile's RAM requirements.
35. [ ] Implement automatic NVMe TRIM/DISCARD execution upon switching to a low-I/O profile.

## Phase 4: Graphics & Display Pipeline (Wayland Native)
36. [ ] Build the "Console Experience": Citadel kills SDDM/KDE and launches `gamescope` directly from a TTY.
37. [ ] Implement dynamic EDID spoofing for headless server profiles.
38. [ ] Write a custom dbus-run-session wrapper to isolate Wayland environments per profile.
39. [ ] Add KMS (Kernel Mode Setting) plane manipulation to inject Citadel overlays directly into the framebuffer.
40. [ ] Build an automatic fallback to X11 for specific legacy CAD/Gaming applications.
41. [ ] Implement dynamic VRR (Variable Refresh Rate) and FreeSync toggling via `wlr-randr`.
42. [ ] Add ICC color profile switching (warm colors for Programming, high-contrast for Gaming).
43. [ ] Build a VRAM defragmentation script that reloads the `amdgpu` or `nvidia` drivers on mode switch.
44. [ ] Implement hardware cursor (HWCursor) forced enabling/disabling to reduce input lag.
45. [ ] Create a "Safe Graphics Mode" that forces `nomodeset` and drops to `fbdev` if the GPU driver crashes.

## Phase 5: Network & Security (Red Team Core)
46. [ ] Implement MAC address randomization automatically on switching to the Red Team profile.
47. [ ] Build a DNS sinkhole (Pi-Hole equivalent) inside Citadel using a local `dnsmasq` instance.
48. [ ] Add forced transparent Tor routing using `iptables` REDIRECT chains for the entire OS.
49. [ ] Implement an eBPF-based packet sniffer that streams live suspicious IPs to the Citadel UI.
50. [ ] Build an SSH tarpit daemon (Endlessh) that automatically starts during Lockdown mode.
51. [ ] Integrate Fail2Ban logs directly into the Citadel gRPC telemetry stream.
52. [ ] Build a custom WireGuard orchestration engine to bind specific apps to VPN namespaces.
53. [ ] Implement a Wi-Fi deauth attack detector that alerts the Citadel UI if the network is under attack.
54. [ ] Create an air-gap mode that literally unbinds the `iwlwifi` and `e1000e` kernel modules.
55. [ ] Add an encrypted DNS-over-HTTPS (DoH) proxy inside the Citadel daemon.
56. [ ] Build a hardware switch integration (if supported by laptop chassis) to trigger Citadel stealth mode.
57. [ ] Implement a honeypot filesystem trap that triggers a system freeze if touched by ransomware.
58. [ ] Add SSL certificate pinning for all internal Citadel gRPC API calls.

## Phase 6: Application & Process Hyper-Orchestration
59. [ ] Rewrite the Cgroups v2 engine to use `systemd.slice` definitions instead of manual `/sys/fs` directories.
60. [ ] Implement OOM (Out Of Memory) killer priority adjustments (protecting the game, sacrificing the browser).
61. [ ] Build a Flatpak permission orchestrator (revoking webcam/mic from all apps during Lockdown).
62. [ ] Add an AppArmor profile generator that dynamically locks down processes based on the Citadel mode.
63. [ ] Implement Wine/Proton prefix swapping for instant isolated game environments.
64. [ ] Build a "Heavy Hitter" preemptive freezer (automatically freezing processes using >20% CPU for >10s).
65. [ ] Integrate Docker socket manipulation to pause all containers simultaneously via `docker pause`.
66. [ ] Create a custom Wayland clipboard manager that clears the clipboard when leaving Programming mode.
67. [ ] Build an input interceptor using `evdev` to implement custom macro keys at the OS level.
68. [ ] Add Pipewire/Wireplumber routing scripts to isolate game audio from Discord audio automatically.

## Phase 7: UI, UX & Telemetry (The Cybernetic Dashboard)
69. [ ] Port the Python GTK UI to a pure Rust/Tauri or C/GTK4 application for zero-latency rendering.
70. [ ] Implement a global OS overlay (like Discord overlay) injected into Gamescope to show Citadel vitals.
71. [ ] Add 3D WebGL/OpenGL accelerated hardware meters for the UI.
72. [ ] Build a system tray icon with a hyper-fast drop-down menu for mode switching.
73. [ ] Integrate a live Network Topology map into the UI using LLDP and ARP tables.
74. [ ] Add a terminal fallback UI (using `rich` or `curses`) for when the display manager is killed.
75. [ ] Implement a command palette (Ctrl+Shift+P style) into the Citadel desktop for instant commands.
76. [ ] Build an audio visualizer that reacts to the system's pulse audio streams.
77. [ ] Add haptic feedback integration for gamepads when profiles switch successfully.
78. [ ] Build a unified Notification Daemon that replaces `dunst` to handle all OS alerts.
79. [ ] Implement a "First Boot" OOBE (Out Of Box Experience) installer for PhazeOS.
80. [ ] Add live interactive process killing (click a bar on the CPU chart to instantly `kill -9` it).

## Phase 8: Package Management & OS Upgrades
81. [ ] Build `citadel-pkg`, a wrapper around `apt` or `pacman` that takes a ZFS snapshot before any upgrade.
82. [ ] Implement immutable OS delta updates (similar to OSTree/NixOS) managed by Citadel.
83. [ ] Add automated rollback detection (if the kernel panics on boot, reboot into the previous snapshot).
84. [ ] Build a local package cache proxy to speed up multiple VM/container installations.
85. [ ] Implement dotfiles synchronization to a self-hosted Git repository upon mode switch.
86. [ ] Add a visual diff generator for `/etc` configurations before applying system updates.

## Phase 9: AI & Autonomous Orchestration
87. [ ] Integrate a local tiny LLM (Llama.cpp) directly into the Citadel Daemon to predict user behavior.
88. [ ] Build an anomaly detection engine that flags suspicious network spikes using local ML models.
89. [ ] Add voice command integration ("Citadel, initialize Red Team Protocol") using Whisper.
90. [ ] Implement automatic thermal prediction (throttling the CPU *before* it hits 90C based on load trajectories).
91. [ ] Build a smart battery optimizer that learns the user's schedule and caps charging at 80% when plugged in.

## Phase 10: Extreme Edge-Cases & Flex Features
92. [ ] Implement multi-monitor independent mode switching (Game on Display 1, Work environment on Display 2).
93. [ ] Build a PXE boot server into Citadel to instantly provision a LAN party with PhazeOS images.
94. [ ] Add a custom kernel boot logo flasher that updates the UEFI splash screen based on the last active profile.
95. [ ] Implement a hardware beep-code (PC speaker) fallback for debugging if the GPU is unbound.
96. [ ] Build a RAM-disk generator (`tmpfs`) that dynamically dumps the currently played Steam game into RAM for 0ms load times.
97. [ ] Add support for dynamically compiling custom kernel modules directly from the Citadel UI.
98. [ ] Implement a "Distraction Free" mode that outright unbinds the USB bus for secondary monitors and webcams.
99. [ ] Build a decentralized peer-to-peer telemetry mesh (if multiple Citadel OS machines are on the same LAN, they share threat data).
100. [ ] Achieve sentient hyper-visor status.
