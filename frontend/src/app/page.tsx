'use client'

import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Building2, Calculator, Layers, Zap } from 'lucide-react'

export default function HomePage() {
  const router = useRouter()
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Building2 className="h-8 w-8 text-primary" />
              <h1 className="text-2xl font-bold text-gray-900">StruMind</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" onClick={() => router.push('/auth/login')}>
                Sign In
              </Button>
              <Button onClick={() => router.push('/auth/signup')}>
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-5xl font-bold text-gray-900 mb-6">
            Next-Generation
            <span className="text-primary block">Structural Engineering</span>
          </h2>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            StruMind combines the power of ETABS, STAAD.Pro, and Tekla Structures into one 
            unified AI-powered cloud-native platform for structural analysis, design, and BIM.
          </p>
          <div className="flex justify-center space-x-4">
            <Button size="lg" className="px-8" onClick={() => router.push('/auth/signup')}>
              Start Free Trial
            </Button>
            <Button size="lg" variant="outline" className="px-8" onClick={() => alert('Demo coming soon!')}>
              Watch Demo
            </Button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <h3 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Everything You Need in One Platform
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <Card className="text-center">
              <CardHeader>
                <Calculator className="h-12 w-12 text-primary mx-auto mb-4" />
                <CardTitle>Advanced Analysis</CardTitle>
                <CardDescription>
                  Linear & non-linear static, dynamic, buckling, and P-Delta analysis
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="text-center">
              <CardHeader>
                <Building2 className="h-12 w-12 text-primary mx-auto mb-4" />
                <CardTitle>Smart Design</CardTitle>
                <CardDescription>
                  Automated RC, steel, composite, and foundation design per international codes
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="text-center">
              <CardHeader>
                <Layers className="h-12 w-12 text-primary mx-auto mb-4" />
                <CardTitle>3D BIM Integration</CardTitle>
                <CardDescription>
                  Full IFC 4.x support with seamless CAD and BIM workflow integration
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="text-center">
              <CardHeader>
                <Zap className="h-12 w-12 text-primary mx-auto mb-4" />
                <CardTitle>Cloud-Native</CardTitle>
                <CardDescription>
                  Scalable cloud computing with real-time collaboration and AI assistance
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Capabilities Section */}
      <section className="py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <Card>
              <CardHeader>
                <CardTitle className="text-steel-700">Structural Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• Linear & Non-linear Static Analysis</li>
                  <li>• Modal & Response Spectrum Analysis</li>
                  <li>• Time History Analysis</li>
                  <li>• Buckling & P-Delta Analysis</li>
                  <li>• Wind & Seismic Load Generation</li>
                  <li>• Load Combination Processing</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-concrete-700">Design & Detailing</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• RC Design (IS 456, ACI 318, EC2)</li>
                  <li>• Steel Design (IS 800, AISC 360, EC3)</li>
                  <li>• Foundation & Shear Wall Design</li>
                  <li>• Connection Design (Bolted/Welded)</li>
                  <li>• Reinforcement Detailing</li>
                  <li>• Bar Bending Schedules</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-primary">BIM & Visualization</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• 3D Model Visualization</li>
                  <li>• IFC 4.x Export/Import</li>
                  <li>• DXF & PDF Drawing Export</li>
                  <li>• Real-time Result Visualization</li>
                  <li>• Deformed Shapes & Diagrams</li>
                  <li>• Interactive 3D Viewer</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Building2 className="h-6 w-6" />
                <span className="text-xl font-bold">StruMind</span>
              </div>
              <p className="text-gray-400">
                Next-generation structural engineering platform
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-gray-400">
                <li>Features</li>
                <li>Pricing</li>
                <li>Documentation</li>
                <li>API</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-gray-400">
                <li>About</li>
                <li>Blog</li>
                <li>Careers</li>
                <li>Contact</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Support</h4>
              <ul className="space-y-2 text-gray-400">
                <li>Help Center</li>
                <li>Community</li>
                <li>Status</li>
                <li>Security</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 StruMind. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}