#!/usr/bin/env python3
"""
StruMind Complete Workflow Demo - Master Script
Runs all 5 parts of the video demonstration sequentially.
"""

import asyncio
import subprocess
import time
from pathlib import Path
from datetime import datetime

class MasterVideoDemo:
    def __init__(self):
        self.recordings_dir = Path("./recordings")
        self.recordings_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.parts = [
            {
                "script": "part_1_login_demo.py",
                "name": "User Login & Authentication",
                "description": "Demonstrates user login and dashboard access"
            },
            {
                "script": "part_2_project_creation.py", 
                "name": "Project Creation & Model Setup",
                "description": "Shows project creation and structural model setup"
            },
            {
                "script": "part_3_structural_analysis.py",
                "name": "Structural Analysis",
                "description": "Demonstrates analysis execution and results viewing"
            },
            {
                "script": "part_4_design_optimization.py",
                "name": "Design Optimization",
                "description": "Shows design optimization and code compliance"
            },
            {
                "script": "part_5_export_reporting.py",
                "name": "Export & Reporting", 
                "description": "Demonstrates final export and project completion"
            }
        ]

    def run_part(self, part_info):
        """Run a single part of the demo"""
        print(f"\n{'='*60}")
        print(f"🎬 STARTING: {part_info['name']}")
        print(f"📝 {part_info['description']}")
        print(f"🎯 Script: {part_info['script']}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run the part script
            result = subprocess.run(
                ["python", part_info["script"]], 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout per part
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ COMPLETED: {part_info['name']} ({duration:.1f}s)")
                print(f"📹 Video recorded successfully")
                return True
            else:
                print(f"❌ FAILED: {part_info['name']}")
                print(f"Error output: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {part_info['name']} exceeded 5 minutes")
            return False
        except Exception as e:
            print(f"💥 EXCEPTION: {part_info['name']} - {e}")
            return False

    def generate_summary_report(self, results):
        """Generate a summary report of all video parts"""
        report = {
            "timestamp": self.timestamp,
            "total_parts": len(self.parts),
            "successful_parts": sum(results),
            "failed_parts": len(results) - sum(results),
            "parts": []
        }
        
        for i, (part_info, success) in enumerate(zip(self.parts, results)):
            part_result = {
                "part_number": i + 1,
                "name": part_info["name"],
                "script": part_info["script"],
                "description": part_info["description"],
                "status": "SUCCESS" if success else "FAILED"
            }
            report["parts"].append(part_result)
        
        # Save report
        import json
        report_file = self.recordings_dir / f"video_demo_report_{self.timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

    def list_generated_videos(self):
        """List all generated video files"""
        video_files = list(self.recordings_dir.glob("*.webm"))
        video_files.sort(key=lambda x: x.stat().st_mtime)
        
        print(f"\n📹 Generated Video Files:")
        print(f"{'='*60}")
        
        for video_file in video_files:
            size_mb = video_file.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(video_file.stat().st_mtime)
            print(f"📄 {video_file.name}")
            print(f"   Size: {size_mb:.1f} MB")
            print(f"   Created: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

    def run_complete_demo(self):
        """Run the complete video demonstration"""
        print("🎬 StruMind Complete Workflow Video Demo")
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Recordings directory: {self.recordings_dir}")
        print(f"🎯 Total parts to record: {len(self.parts)}")
        
        overall_start = time.time()
        results = []
        
        # Run each part
        for i, part_info in enumerate(self.parts, 1):
            print(f"\n🎬 Part {i}/{len(self.parts)}")
            success = self.run_part(part_info)
            results.append(success)
            
            # Brief pause between parts
            if i < len(self.parts):
                print("⏸️ Pausing 5 seconds before next part...")
                time.sleep(5)
        
        overall_end = time.time()
        total_duration = overall_end - overall_start
        
        # Generate summary
        report = self.generate_summary_report(results)
        
        # Print final summary
        print(f"\n{'='*60}")
        print("🎉 COMPLETE WORKFLOW DEMO FINISHED")
        print(f"{'='*60}")
        print(f"⏱️ Total Duration: {total_duration/60:.1f} minutes")
        print(f"✅ Successful Parts: {report['successful_parts']}/{report['total_parts']}")
        print(f"❌ Failed Parts: {report['failed_parts']}/{report['total_parts']}")
        
        if report['successful_parts'] == report['total_parts']:
            print("🎊 ALL PARTS COMPLETED SUCCESSFULLY!")
        else:
            print("⚠️ Some parts failed - check individual logs")
        
        # List generated videos
        self.list_generated_videos()
        
        print(f"\n📊 Summary report saved: video_demo_report_{self.timestamp}.json")
        print(f"📁 All files in: {self.recordings_dir}")
        
        return report

if __name__ == "__main__":
    demo = MasterVideoDemo()
    report = demo.run_complete_demo()