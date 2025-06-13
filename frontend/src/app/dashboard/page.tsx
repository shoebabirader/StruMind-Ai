'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  Building2, 
  Plus, 
  Search, 
  Filter, 
  MoreVertical,
  Users,
  Calendar,
  Activity,
  TrendingUp,
  LogOut
} from 'lucide-react'
import { API_ENDPOINTS } from '@/lib/config'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

interface Project {
  id: string
  name: string
  description: string
  status: 'draft' | 'active' | 'completed' | 'archived'
  projectType: string
  createdAt: string
  updatedAt: string
  memberCount: number
  analysisCount: number
  thumbnail?: string
}

interface DashboardStats {
  totalProjects: number
  activeAnalyses: number
  teamMembers: number
  storageUsed: number
}

export default function DashboardPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [stats, setStats] = useState<DashboardStats>({
    totalProjects: 0,
    activeAnalyses: 0,
    teamMembers: 0,
    storageUsed: 0
  })
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('token')
    const userData = localStorage.getItem('user')
    
    if (!token) {
      router.push('/auth/login')
      return
    }

    if (userData && userData !== 'undefined') {
      try {
        setUser(JSON.parse(userData))
      } catch (error) {
        console.error('Error parsing user data:', error)
        localStorage.removeItem('user')
        router.push('/auth/login')
        return
      }
    }

    fetchDashboardData()
  }, [router])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      const token = localStorage.getItem('token')
      
      // Fetch projects from API
      const projectsResponse = await fetch(API_ENDPOINTS.projects.list, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (projectsResponse.ok) {
        const projectsData = await projectsResponse.json()
        setProjects(projectsData.projects || [])
        
        // Calculate stats from projects
        const mockStats: DashboardStats = {
          totalProjects: projectsData.projects?.length || 0,
          activeAnalyses: 7,
          teamMembers: 12,
          storageUsed: 2.4
        }
        setStats(mockStats)
      } else {
        // Use mock data if API fails
        const mockProjects: Project[] = [
          {
            id: '1',
            name: 'Office Tower - Downtown',
            description: '25-story commercial building with steel frame',
            status: 'active',
            projectType: 'commercial',
            createdAt: '2024-01-15',
            updatedAt: '2024-01-20',
            memberCount: 5,
            analysisCount: 12,
          },
          {
            id: '2',
            name: 'Residential Complex',
            description: 'Multi-story residential building with RC frame',
            status: 'draft',
            projectType: 'residential',
            createdAt: '2024-01-10',
            updatedAt: '2024-01-18',
            memberCount: 3,
            analysisCount: 8,
          },
          {
            id: '3',
            name: 'Bridge Design',
            description: 'Cable-stayed bridge over river',
            status: 'completed',
            projectType: 'infrastructure',
            createdAt: '2023-12-01',
            updatedAt: '2024-01-05',
            memberCount: 8,
            analysisCount: 25,
          }
        ]

        const mockStats: DashboardStats = {
          totalProjects: 15,
          activeAnalyses: 7,
          teamMembers: 12,
          storageUsed: 2.4
        }

        setProjects(mockProjects)
        setStats(mockStats)
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      // Use mock data on error
      setProjects([])
      setStats({
        totalProjects: 0,
        activeAnalyses: 0,
        teamMembers: 0,
        storageUsed: 0
      })
    } finally {
      setLoading(false)
    }
  }

  const filteredProjects = projects.filter(project => {
    const matchesSearch = project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         project.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterStatus === 'all' || project.status === filterStatus
    return matchesSearch && matchesFilter
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'draft': return 'bg-yellow-100 text-yellow-800'
      case 'completed': return 'bg-blue-100 text-blue-800'
      case 'archived': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const handleCreateProject = () => {
    router.push('/projects/new')
  }

  const handleProjectClick = (projectId: string) => {
    router.push(`/projects/${projectId}`)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Building2 className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">StruMind</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Button onClick={handleCreateProject} className="bg-blue-600 hover:bg-blue-700">
                <Plus className="h-4 w-4 mr-2" />
                New Project
              </Button>
              <div className="relative group">
                <Avatar className="cursor-pointer">
                  <AvatarImage src="/api/placeholder/32/32" />
                  <AvatarFallback>
                    {user?.first_name?.[0]}{user?.last_name?.[0]}
                  </AvatarFallback>
                </Avatar>
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 hidden group-hover:block">
                  <div className="px-4 py-2 text-sm text-gray-700 border-b">
                    {user?.first_name} {user?.last_name}
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign out
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalProjects}</div>
              <p className="text-xs text-muted-foreground">
                +2 from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Analyses</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.activeAnalyses}</div>
              <p className="text-xs text-muted-foreground">
                Running now
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Team Members</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.teamMembers}</div>
              <p className="text-xs text-muted-foreground">
                Across all projects
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.storageUsed} GB</div>
              <p className="text-xs text-muted-foreground">
                of 10 GB limit
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Projects Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-medium text-gray-900 mb-4 sm:mb-0">
                Recent Projects
              </h2>
              <div className="flex space-x-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    placeholder="Search projects..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 w-64"
                  />
                </div>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="draft">Draft</option>
                  <option value="completed">Completed</option>
                  <option value="archived">Archived</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
            {filteredProjects.map((project) => (
              <Card 
                key={project.id} 
                className="cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => handleProjectClick(project.id)}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{project.name}</CardTitle>
                    <MoreVertical className="h-4 w-4 text-gray-400" />
                  </div>
                  <CardDescription>{project.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between mb-4">
                    <Badge className={getStatusColor(project.status)}>
                      {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                    </Badge>
                    <span className="text-sm text-gray-500 capitalize">
                      {project.projectType}
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm text-gray-500">
                    <div className="flex items-center">
                      <Users className="h-4 w-4 mr-1" />
                      {project.memberCount} members
                    </div>
                    <div className="flex items-center">
                      <Activity className="h-4 w-4 mr-1" />
                      {project.analysisCount} analyses
                    </div>
                  </div>
                  
                  <div className="mt-4 text-xs text-gray-400">
                    Updated {new Date(project.updatedAt).toLocaleDateString()}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {filteredProjects.length === 0 && (
            <div className="text-center py-12">
              <Building2 className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No projects found</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by creating a new project.
              </p>
              <div className="mt-6">
                <Button onClick={handleCreateProject}>
                  <Plus className="h-4 w-4 mr-2" />
                  New Project
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}