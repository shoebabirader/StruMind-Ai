'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Building2, 
  Calculator, 
  Settings, 
  FileText, 
  Download, 
  Play,
  ArrowLeft,
  Edit,
  Share,
  MoreVertical
} from 'lucide-react';
// Remove useAuth import - using localStorage directly
import { API_ENDPOINTS } from '@/lib/config';

interface Project {
  id: string;
  name: string;
  description: string;
  location: string;
  project_type: string;
  design_code_concrete: string;
  design_code_steel: string;
  design_code_seismic: string;
  status: string;
  created_at: string;
  updated_at: string;
  owner_id: string;
  organization_id: string;
}

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const projectId = params.id as string;

  useEffect(() => {
    const fetchProject = async () => {
      const token = localStorage.getItem('token');
      if (!token || !projectId) {
        router.push('/auth/login');
        return;
      }

      try {
        setLoading(true);
        const response = await fetch(API_ENDPOINTS.projects.get(projectId), {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch project');
        }

        const data = await response.json();
        setProject(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [projectId, router]);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return 'Unknown';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'completed':
        return 'bg-blue-100 text-blue-800';
      case 'archived':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading project...</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Project Not Found</h1>
          <p className="text-gray-600 mb-6">{error || 'The project you are looking for does not exist.'}</p>
          <Button onClick={() => router.push('/dashboard')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/dashboard')}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
                <p className="text-gray-600">{project.description}</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Badge className={getStatusColor(project.status)}>
                {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
              </Badge>
              <Button variant="outline" size="sm">
                <Share className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button variant="outline" size="sm">
                <Edit className="w-4 h-4 mr-2" />
                Edit
              </Button>
              <Button variant="outline" size="sm">
                <MoreVertical className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-3">
            <Tabs defaultValue="overview" className="space-y-6">
              <TabsList className="grid w-full grid-cols-5">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="modeling">Modeling</TabsTrigger>
                <TabsTrigger value="analysis">Analysis</TabsTrigger>
                <TabsTrigger value="design">Design</TabsTrigger>
                <TabsTrigger value="reports">Reports</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <Building2 className="w-5 h-5 mr-2" />
                        Project Information
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <label className="text-sm font-medium text-gray-500">Location</label>
                        <p className="text-gray-900">{project.location || 'Not specified'}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Project Type</label>
                        <p className="text-gray-900 capitalize">{project.project_type}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Created</label>
                        <p className="text-gray-900">{formatDate(project.created_at)}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Last Updated</label>
                        <p className="text-gray-900">{formatDate(project.updated_at)}</p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <Settings className="w-5 h-5 mr-2" />
                        Design Codes
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <label className="text-sm font-medium text-gray-500">Concrete Design</label>
                        <p className="text-gray-900">{project.design_code_concrete}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Steel Design</label>
                        <p className="text-gray-900">{project.design_code_steel}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Seismic Design</label>
                        <p className="text-gray-900">{project.design_code_seismic}</p>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Quick Actions</CardTitle>
                    <CardDescription>
                      Get started with your structural engineering project
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Button className="h-20 flex-col space-y-2">
                        <Building2 className="w-6 h-6" />
                        <span>Start Modeling</span>
                      </Button>
                      <Button variant="outline" className="h-20 flex-col space-y-2">
                        <Calculator className="w-6 h-6" />
                        <span>Run Analysis</span>
                      </Button>
                      <Button variant="outline" className="h-20 flex-col space-y-2">
                        <FileText className="w-6 h-6" />
                        <span>Generate Report</span>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="modeling">
                <Card>
                  <CardHeader>
                    <CardTitle>3D Structural Model</CardTitle>
                    <CardDescription>
                      Create and edit your structural model with nodes, elements, and loads
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-96 bg-gray-100 rounded-lg flex items-center justify-center">
                      <div className="text-center">
                        <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">3D Model Viewer</h3>
                        <p className="text-gray-600 mb-4">Start building your structural model</p>
                        <Button>
                          <Play className="w-4 h-4 mr-2" />
                          Launch Model Editor
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="analysis">
                <Card>
                  <CardHeader>
                    <CardTitle>Structural Analysis</CardTitle>
                    <CardDescription>
                      Configure and run structural analysis
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Linear Static Analysis</h4>
                          <p className="text-sm text-gray-600 mb-3">Basic structural analysis under static loads</p>
                          <Button size="sm">Configure</Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Modal Analysis</h4>
                          <p className="text-sm text-gray-600 mb-3">Natural frequencies and mode shapes</p>
                          <Button size="sm" variant="outline">Configure</Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Response Spectrum</h4>
                          <p className="text-sm text-gray-600 mb-3">Seismic response analysis</p>
                          <Button size="sm" variant="outline">Configure</Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">P-Delta Analysis</h4>
                          <p className="text-sm text-gray-600 mb-3">Second-order effects analysis</p>
                          <Button size="sm" variant="outline">Configure</Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="design">
                <Card>
                  <CardHeader>
                    <CardTitle>Structural Design</CardTitle>
                    <CardDescription>
                      Design structural elements according to codes
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Concrete Design</h4>
                          <p className="text-sm text-gray-600 mb-3">RC beam, column, and slab design</p>
                          <Button size="sm">Start Design</Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Steel Design</h4>
                          <p className="text-sm text-gray-600 mb-3">Steel member and connection design</p>
                          <Button size="sm" variant="outline">Start Design</Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Foundation Design</h4>
                          <p className="text-sm text-gray-600 mb-3">Footing and pile foundation design</p>
                          <Button size="sm" variant="outline">Start Design</Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Shear Wall Design</h4>
                          <p className="text-sm text-gray-600 mb-3">Reinforced concrete shear wall design</p>
                          <Button size="sm" variant="outline">Start Design</Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="reports">
                <Card>
                  <CardHeader>
                    <CardTitle>Reports & Documentation</CardTitle>
                    <CardDescription>
                      Generate analysis and design reports
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Analysis Report</h4>
                          <p className="text-sm text-gray-600 mb-3">Comprehensive structural analysis results</p>
                          <Button size="sm">
                            <Download className="w-4 h-4 mr-2" />
                            Generate PDF
                          </Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Design Report</h4>
                          <p className="text-sm text-gray-600 mb-3">Design calculations and code checks</p>
                          <Button size="sm" variant="outline">
                            <Download className="w-4 h-4 mr-2" />
                            Generate PDF
                          </Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">Drawings</h4>
                          <p className="text-sm text-gray-600 mb-3">Structural drawings and details</p>
                          <Button size="sm" variant="outline">
                            <Download className="w-4 h-4 mr-2" />
                            Export DXF
                          </Button>
                        </div>
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-medium mb-2">BIM Model</h4>
                          <p className="text-sm text-gray-600 mb-3">3D BIM model export</p>
                          <Button size="sm" variant="outline">
                            <Download className="w-4 h-4 mr-2" />
                            Export IFC
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Project Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Nodes</span>
                  <span className="font-medium">0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Elements</span>
                  <span className="font-medium">0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Load Cases</span>
                  <span className="font-medium">0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Analyses</span>
                  <span className="font-medium">0</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-sm text-gray-600">No recent activity</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}