'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Building2, ArrowLeft } from 'lucide-react'
import { API_ENDPOINTS } from '@/lib/config'

export default function NewProjectPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    projectType: 'commercial',
    location: '',
    client: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const token = localStorage.getItem('token')
      
      // Transform form data to match API expectations
      const apiData = {
        name: formData.name,
        description: formData.description,
        project_type: formData.projectType,
        location: formData.location,
        client: formData.client
      }
      
      const response = await fetch(API_ENDPOINTS.projects.create, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apiData),
      })

      if (response.ok) {
        const data = await response.json()
        // Redirect to the new project
        router.push(`/projects/${data.id}`)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to create project')
      }
    } catch (error) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center py-6">
            <Button 
              variant="ghost" 
              onClick={() => router.push('/dashboard')}
              className="mr-4"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
            <div className="flex items-center">
              <Building2 className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">Create New Project</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Project Details</CardTitle>
            <CardDescription>
              Create a new structural engineering project
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md text-sm">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <label htmlFor="name" className="text-sm font-medium text-gray-700">
                  Project Name *
                </label>
                <Input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter project name"
                  required
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="description" className="text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Enter project description"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label htmlFor="projectType" className="text-sm font-medium text-gray-700">
                    Project Type *
                  </label>
                  <select
                    id="projectType"
                    name="projectType"
                    value={formData.projectType}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  >
                    <option value="commercial">Commercial</option>
                    <option value="residential">Residential</option>
                    <option value="industrial">Industrial</option>
                    <option value="infrastructure">Infrastructure</option>
                    <option value="institutional">Institutional</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label htmlFor="location" className="text-sm font-medium text-gray-700">
                    Location
                  </label>
                  <Input
                    id="location"
                    name="location"
                    type="text"
                    value={formData.location}
                    onChange={handleChange}
                    placeholder="Project location"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="client" className="text-sm font-medium text-gray-700">
                  Client
                </label>
                <Input
                  id="client"
                  name="client"
                  type="text"
                  value={formData.client}
                  onChange={handleChange}
                  placeholder="Client name"
                />
              </div>

              <div className="flex justify-end space-x-4 pt-6">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => router.push('/dashboard')}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={loading}>
                  {loading ? 'Creating...' : 'Create Project'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}