#!/usr/bin/env python3
import sys
import grpc
import argparse
import os

# Add path so it finds protocol buffer files
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'services/hub'))
import citadel_pb2
import citadel_pb2_grpc

def status():
    channel = grpc.insecure_channel('localhost:50051')
    stub = citadel_pb2_grpc.CitadelServiceStub(channel)
    try:
        response = stub.GetCurrentState(citadel_pb2.StateRequest())
        print(f"Active Profile: {response.active_profile}")
        print(f"Uptime: {response.uptime_seconds:.1f} seconds")
        print("Active Services:")
        for svc, active in response.active_services.items():
            print(f"  {svc}: {'[UP]' if active else '[DOWN]'}")
    except grpc.RpcError as e:
        print(f"Error connecting to Hub: {e.details()}")

def set_profile(name):
    channel = grpc.insecure_channel('localhost:50051')
    stub = citadel_pb2_grpc.CitadelServiceStub(channel)
    try:
        req = citadel_pb2.SetProfileRequest(profile_name=name)
        response = stub.SetProfile(req)
        print(f"Result: {response.message}")
    except grpc.RpcError as e:
        print(f"Error connecting to Hub: {e.details()}")

def monitor():
    channel = grpc.insecure_channel('localhost:50051')
    stub = citadel_pb2_grpc.CitadelServiceStub(channel)
    try:
        print("Monitoring Telemetry Stream (Press Ctrl+C to stop)...")
        req = citadel_pb2.TelemetryRequest(interval_ms=1000)
        for pulse in stub.StreamTelemetry(req):
            cpu_avg = sum(pulse.cpu.core_usage) / len(pulse.cpu.core_usage) if pulse.cpu.core_usage else 0
            vram_mb = pulse.gpu.vram_used_bytes // (1024 * 1024)
            ram_mb = pulse.ram.used_bytes // (1024 * 1024)
            net_kbps = pulse.net_speed_bytes_sec / 1024
            print(f"[CPU] {cpu_avg:.1f}%  |  [GPU] {pulse.gpu.temperature}°C, {vram_mb}MB VRAM  |  [RAM] {ram_mb}MB  |  [NET] {net_kbps:.1f} KB/s")
    except grpc.RpcError as e:
        print(f"Error connecting to Hub: {e.details()}")
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Citadel Hub CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    status_parser = subparsers.add_parser("status", help="Get current status")
    
    set_parser = subparsers.add_parser("set", help="Set active profile")
    set_parser.add_argument("profile", help="Profile name (e.g. Default, Performance, Stealth)")
    
    monitor_parser = subparsers.add_parser("monitor", help="Stream live telemetry")
    
    args = parser.parse_args()
    
    if args.command == "status":
        status()
    elif args.command == "set":
        set_profile(args.profile)
    elif args.command == "monitor":
        monitor()
    else:
        parser.print_help()
