#!/usr/bin/env python3

import requests
import json

# Test element creation specifically
base_url = "http://localhost:8000"

# First, register and login
register_data = {
    "email": "debug@test.com",
    "password": "testpass123",
    "first_name": "Debug",
    "last_name": "User",
    "organization_name": "Debug Org"
}

response = requests.post(f"{base_url}/api/v1/auth/register", json=register_data)
print(f"Register: {response.status_code}")
if response.status_code == 200:
    # Registration successful, token included
    token_data = response.json()
    token = token_data["access_token"]
    print("Registration successful, using token from registration")
else:
    print(f"Register failed: {response.text}")
    # Try login instead
    login_data = {
        "email": "debug@test.com",
        "password": "testpass123"
    }

    response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data)
    print(f"Login: {response.status_code}")
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        exit(1)
    token_data = response.json()
    token = token_data["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create project
project_data = {
    "name": "Debug Project",
    "description": "Debug project for element testing"
}

response = requests.post(f"{base_url}/api/v1/projects", json=project_data, headers=headers)
project = response.json()
project_id = project["id"]
print(f"Project created: {project_id}")

# Create nodes
nodes = []
for i, (x, y, z) in enumerate([(0, 0, 0), (5, 0, 0), (10, 0, 0), (15, 0, 0)]):
    node_data = {
        "x": x, 
        "y": y, 
        "z": z,
        "label": f"N{i+1}"
    }
    response = requests.post(f"{base_url}/api/v1/models/{project_id}/nodes", json=node_data, headers=headers)
    if response.status_code in [200, 201]:
        node = response.json()
        nodes.append(node)
        print(f"Node created: {node['id']}")
    else:
        print(f"Node creation failed: {response.status_code}")

# Create material
material_data = {
    "name": "Steel S355",
    "material_type": "steel",
    "properties": {
        "elastic_modulus": 200e9,
        "poisson_ratio": 0.3,
        "density": 7850,
        "yield_strength": 355e6
    }
}

response = requests.post(f"{base_url}/api/v1/models/{project_id}/materials", json=material_data, headers=headers)
if response.status_code in [200, 201]:
    material = response.json()
    print(f"Material created: {material['id']}")
else:
    print(f"Material creation failed: {response.status_code}")

# Create section
section_data = {
    "name": "IPE 300",
    "section_type": "i_section",
    "properties": {
        "area": 0.0053,
        "moment_of_inertia_x": 8.356e-5,
        "moment_of_inertia_y": 6.04e-6,
        "torsional_constant": 2.07e-7
    }
}

response = requests.post(f"{base_url}/api/v1/models/{project_id}/sections", json=section_data, headers=headers)
if response.status_code in [200, 201]:
    section = response.json()
    print(f"Section created: {section['id']}")
else:
    print(f"Section creation failed: {response.status_code}")

# Now try to create element
if len(nodes) >= 2:
    element_data = {
        "start_node_id": nodes[0]["id"],
        "end_node_id": nodes[1]["id"],
        "material_id": material["id"],
        "section_id": section["id"],
        "element_type": "beam"
    }
    
    print(f"Attempting to create element with data: {json.dumps(element_data, indent=2)}")
    
    response = requests.post(f"{base_url}/api/v1/models/{project_id}/elements", json=element_data, headers=headers)
    print(f"Element creation response: {response.status_code}")
    if response.status_code != 200 and response.status_code != 201:
        print(f"Response text: {response.text}")
    else:
        element = response.json()
        print(f"Element created: {element['id']}")