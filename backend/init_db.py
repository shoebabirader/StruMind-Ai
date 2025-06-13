#!/usr/bin/env python3
"""
Database initialization script for StruMind backend
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import sync_engine, Base
from db.models.user import User
from db.models.project import Project
from db.models.structural import *
from db.models.analysis import *
from db.models.design import *
from db.models.bim import *

def init_database():
    """Initialize the database with all tables"""
    print("🚀 Initializing StruMind database...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=sync_engine)
        print("✅ Database tables created successfully!")
        
        # Print created tables
        print("\n📋 Created tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
            
        print("\n🎯 Database initialization completed!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()