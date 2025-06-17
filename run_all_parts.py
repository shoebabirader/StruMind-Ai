#!/usr/bin/env python3
"""
StruMind Platform - Complete Multi-Part Demo Runner
Runs all 5 parts of the StruMind workflow demonstration
"""

import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path

class StruMindMultiPartDemo:
    def __init__(self):
        self.videos_dir = Path("./videos")
        self.videos_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.parts = [
            {
                "name": "Part 1: User Onboarding",
                "script": "part_1_signup_login.py",
                "description": "User signup, verification, and login process"
            },
            {
                "name": "Part 2: Project & Modeling",
                "script": "part_2_modeling.py", 
                "description": "Project creation and structural modeling"
            },
            {
                "name": "Part 3: Analysis Engine",
                "script": "part_3_analysis.py",
                "description": "Structural analysis execution and results"
            },
            {
                "name": "Part 4: Design Engine",
                "script": "part_4_design.py",
                "description": "Code-based design checks and verification"
            },
            {
                "name": "Part 5: Export & Reporting",
                "script": "part_5_export.py",
                "description": "Report generation and export functionality"
            }
        ]

    async def run_part(self, part_info):
        """Run a single part of the demo"""
        print(f"\n{'='*80}")
        print(f"🎬 STARTING {part_info['name'].upper()}")
        print(f"📝 {part_info['description']}")
        print(f"{'='*80}")
        
        try:
            # Run the part script
            result = subprocess.run([
                sys.executable, part_info['script']
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ {part_info['name']} completed successfully!")
                print("📤 Output:")
                print(result.stdout)
                return True
            else:
                print(f"❌ {part_info['name']} failed!")
                print("📤 Error output:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {part_info['name']} timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"❌ {part_info['name']} failed with exception: {e}")
            return False

    async def run_all_parts(self):
        """Run all parts of the demo"""
        print("🚀 Starting Complete StruMind Multi-Part Demo")
        print(f"📅 Session timestamp: {self.timestamp}")
        print(f"📁 Videos will be saved to: {self.videos_dir}")
        
        results = []
        successful_parts = 0
        
        for i, part in enumerate(self.parts, 1):
            print(f"\n🎯 Running {i}/{len(self.parts)}: {part['name']}")
            
            success = await self.run_part(part)
            results.append({
                "part": part['name'],
                "success": success,
                "description": part['description']
            })
            
            if success:
                successful_parts += 1
                print(f"✅ Part {i} completed successfully")
            else:
                print(f"❌ Part {i} failed")
            
            # Small delay between parts
            await asyncio.sleep(2)
        
        # Generate summary
        await self.generate_summary(results, successful_parts)
        
        return successful_parts == len(self.parts)

    async def generate_summary(self, results, successful_parts):
        """Generate a summary of all parts"""
        print("\n" + "="*80)
        print("📊 STRUMIND MULTI-PART DEMO SUMMARY")
        print("="*80)
        
        print(f"📈 Success Rate: {successful_parts}/{len(self.parts)} parts completed")
        print(f"📅 Session: {self.timestamp}")
        
        print("\n📋 Part-by-Part Results:")
        for i, result in enumerate(results, 1):
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            print(f"  {i}. {result['part']}: {status}")
            print(f"     {result['description']}")
        
        # List generated videos
        video_files = list(self.videos_dir.glob("part-*.webm"))
        if video_files:
            print(f"\n🎬 Generated Videos ({len(video_files)}):")
            for video in sorted(video_files):
                size_kb = video.stat().st_size / 1024
                print(f"  📹 {video.name} ({size_kb:.1f} KB)")
        else:
            print("\n⚠️ No video files found")
        
        print("\n" + "="*80)
        
        if successful_parts == len(self.parts):
            print("🎉 ALL PARTS COMPLETED SUCCESSFULLY!")
            print("✨ Complete StruMind workflow demonstration ready!")
        else:
            print(f"⚠️ {len(self.parts) - successful_parts} part(s) failed")
            print("🔧 Check individual part outputs for details")
        
        print("="*80)

async def main():
    """Main function to run all demo parts"""
    demo = StruMindMultiPartDemo()
    
    try:
        success = await demo.run_all_parts()
        return success
    except Exception as e:
        print(f"\n❌ Multi-part demo failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)