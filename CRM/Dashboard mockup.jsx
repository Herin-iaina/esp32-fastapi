import React, { useState } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Activity, TrendingUp, Users, Package, DollarSign, AlertCircle, ThermometerSun, Droplets, ShoppingCart, Truck, CheckCircle, Clock } from 'lucide-react';

// Données mockées pour la démonstration
const mockData = {
    // Statistiques globales
    stats: {
        activeIncubators: 4,
        totalEggs: 1240,
        expectedHatch: 1089,
        hatchRate: 87.8,
        dailyRevenue: 850000,
        pendingOrders: 12,
        activeSuppliers: 8,
        activeCustomers: 23
    },

    // Performance incubateurs sur 7 jours
    incubatorPerformance: [
        { date: '24 Jan', temp: 37.5, humidity: 65, eggs: 300 },
        { date: '25 Jan', temp: 37.6, humidity: 64, eggs: 310 },
        { date: '26 Jan', temp: 37.4, humidity: 66, eggs: 320 },
        { date: '27 Jan', temp: 37.5, humidity: 65, eggs: 330 },
        { date: '28 Jan', temp: 37.7, humidity: 63, eggs: 340 },
        { date: '29 Jan', temp: 37.5, humidity: 65, eggs: 350 },
        { date: '30 Jan', temp: 37.6, humidity: 64, eggs: 360 }
    ],

    // Revenus mensuels
    monthlyRevenue: [
        { month: 'Juil', revenue: 2400000, costs: 1800000 },
        { month: 'Août', revenue: 2800000, costs: 2000000 },
        { month: 'Sept', revenue: 3200000, costs: 2200000 },
        { month: 'Oct', revenue: 3500000, costs: 2400000 },
        { month: 'Nov', revenue: 3800000, costs: 2500000 },
        { month: 'Déc', revenue: 4200000, costs: 2700000 },
        { month: 'Jan', revenue: 4500000, costs: 2800000 }
    ],

    // Distribution des commandes
    ordersByStatus: [
        { name: 'En attente', value: 5, color: '#fbbf24' },
        { name: 'En production', value: 7, color: '#3b82f6' },
        { name: 'Prêt', value: 3, color: '#10b981' },
        { name: 'Livré', value: 35, color: '#6b7280' }
    ],

    // Top 5 clients
    topCustomers: [
        { name: 'Ferme Razafy', orders: 45, revenue: 12500000 },
        { name: 'Elevage Rabe', orders: 38, revenue: 9800000 },
        { name: 'Poulailler Express', orders: 32, revenue: 8200000 },
        { name: 'Volailles du Sud', orders: 28, revenue: 7100000 },
        { name: 'Agro-Élevage Pro', orders: 24, revenue: 6400000 }
    ],

    // Performance fournisseurs
    supplierPerformance: [
        { name: 'Œufs Premium', rating: 4.8, onTime: 95, quality: 4.9 },
        { name: 'Avicole Pro', rating: 4.5, onTime: 88, quality: 4.6 },
        { name: 'Ferme Bio', rating: 4.2, onTime: 82, quality: 4.3 },
        { name: 'Œufs du Nord', rating: 3.9, onTime: 78, quality: 4.0 }
    ],

    // Lots en cours
    activeBatches: [
        { id: 'LOT-2024-015', incubator: 'INC-01', eggs: 320, day: 12, progress: 60, status: 'on-track' },
        { id: 'LOT-2024-016', incubator: 'INC-02', eggs: 280, day: 8, progress: 40, status: 'on-track' },
        { id: 'LOT-2024-017', incubator: 'INC-03', eggs: 310, day: 18, progress: 90, status: 'warning' },
        { id: 'LOT-2024-018', incubator: 'INC-04', eggs: 330, day: 5, progress: 25, status: 'on-track' }
    ],

    // Commandes récentes
    recentOrders: [
        { id: 'CMD-2024-089', customer: 'Ferme Razafy', items: 500, amount: 1000000, status: 'confirmed', date: '2024-01-30' },
        { id: 'CMD-2024-088', customer: 'Elevage Rabe', items: 300, amount: 600000, status: 'in_production', date: '2024-01-29' },
        { id: 'CMD-2024-087', customer: 'Poulailler Express', items: 250, amount: 500000, status: 'ready', date: '2024-01-28' }
    ]
};

// Composant carte statistique
const StatCard = ({ icon: Icon, title, value, subtitle, color, trend }) => (
    <div className="bg-white rounded-lg shadow-md p-6 border-l-4" style={{ borderLeftColor: color }}>
        <div className="flex items-center justify-between">
            <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
                <p className="text-3xl font-bold" style={{ color }}>{value}</p>
                {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
            </div>
            <div className="ml-4 p-3 rounded-full" style={{ backgroundColor: `${color}20` }}>
                <Icon size={32} style={{ color }} />
            </div>
        </div>
        {trend && (
            <div className="mt-3 flex items-center text-sm">
                <TrendingUp size={16} className={trend > 0 ? 'text-green-500' : 'text-red-500'} />
                <span className={`ml-1 font-medium ${trend > 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {trend > 0 ? '+' : ''}{trend}%
                </span>
                <span className="ml-1 text-gray-500">vs mois dernier</span>
            </div>
        )}
    </div>
);

// Composant dashboard principal
const IncubatorDashboard = () => {
    const [activeTab, setActiveTab] = useState('overview');

    const tabs = [
        { id: 'overview', label: 'Vue d\'ensemble', icon: Activity },
        { id: 'incubators', label: 'Incubateurs', icon: ThermometerSun },
        { id: 'customers', label: 'Clients', icon: Users },
        { id: 'suppliers', label: 'Fournisseurs', icon: Truck },
        { id: 'analytics', label: 'Analytiques', icon: TrendingUp }
    ];

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
                <div className="max-w-7xl mx-auto px-6 py-6">
                    <h1 className="text-3xl font-bold">Incubateur Management System</h1>
                    <p className="text-blue-100 mt-1">Tableau de bord intégré - IoT & CRM</p>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="flex space-x-8 overflow-x-auto">
                        {tabs.map(tab => {
                            const Icon = tab.icon;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`flex items-center py-4 px-2 border-b-2 font-medium text-sm transition-colors ${activeTab === tab.id
                                            ? 'border-blue-500 text-blue-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                        }`}
                                >
                                    <Icon size={18} className="mr-2" />
                                    {tab.label}
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-7xl mx-auto px-6 py-8">

                {/* VUE D'ENSEMBLE */}
                {activeTab === 'overview' && (
                    <div className="space-y-6">

                        {/* Stats principales */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            <StatCard
                                icon={Activity}
                                title="Incubateurs actifs"
                                value={mockData.stats.activeIncubators}
                                subtitle={`${mockData.stats.totalEggs} œufs en cours`}
                                color="#3b82f6"
                                trend={12}
                            />
                            <StatCard
                                icon={CheckCircle}
                                title="Taux de réussite moyen"
                                value={`${mockData.stats.hatchRate}%`}
                                subtitle="Ce mois-ci"
                                color="#10b981"
                                trend={3.2}
                            />
                            <StatCard
                                icon={DollarSign}
                                title="Revenus aujourd'hui"
                                value={`${(mockData.stats.dailyRevenue / 1000).toFixed(0)}K Ar`}
                                subtitle="12 commandes"
                                color="#f59e0b"
                                trend={8.5}
                            />
                            <StatCard
                                icon={Users}
                                title="Clients actifs"
                                value={mockData.stats.activeCustomers}
                                subtitle={`${mockData.stats.activeSuppliers} fournisseurs`}
                                color="#8b5cf6"
                            />
                        </div>

                        {/* Graphiques principaux */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                            {/* Performance température/humidité */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center">
                                    <ThermometerSun className="mr-2 text-orange-500" size={20} />
                                    Conditions d'incubation (7 jours)
                                </h3>
                                <ResponsiveContainer width="100%" height={250}>
                                    <LineChart data={mockData.incubatorPerformance}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                                        <YAxis yAxisId="left" domain={[35, 40]} tick={{ fontSize: 12 }} />
                                        <YAxis yAxisId="right" orientation="right" domain={[60, 70]} tick={{ fontSize: 12 }} />
                                        <Tooltip />
                                        <Legend />
                                        <Line yAxisId="left" type="monotone" dataKey="temp" stroke="#f59e0b" strokeWidth={2} name="Température (°C)" />
                                        <Line yAxisId="right" type="monotone" dataKey="humidity" stroke="#3b82f6" strokeWidth={2} name="Humidité (%)" />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Revenus vs Coûts */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center">
                                    <DollarSign className="mr-2 text-green-500" size={20} />
                                    Revenus vs Coûts (7 mois)
                                </h3>
                                <ResponsiveContainer width="100%" height={250}>
                                    <AreaChart data={mockData.monthlyRevenue}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                        <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                                        <YAxis tick={{ fontSize: 12 }} />
                                        <Tooltip formatter={(value) => `${(value / 1000000).toFixed(1)}M Ar`} />
                                        <Legend />
                                        <Area type="monotone" dataKey="revenue" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.6} name="Revenus" />
                                        <Area type="monotone" dataKey="costs" stackId="2" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} name="Coûts" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>

                        </div>

                        {/* Lots actifs et commandes récentes */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                            {/* Lots en cours */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Lots d'incubation actifs</h3>
                                <div className="space-y-3">
                                    {mockData.activeBatches.map(batch => (
                                        <div key={batch.id} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                    <p className="font-semibold text-sm">{batch.id}</p>
                                                    <p className="text-xs text-gray-500">{batch.incubator} • {batch.eggs} œufs</p>
                                                </div>
                                                <span className={`text-xs px-2 py-1 rounded-full ${batch.status === 'on-track' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                                                    }`}>
                                                    Jour {batch.day}/21
                                                </span>
                                            </div>
                                            <div className="w-full bg-gray-200 rounded-full h-2">
                                                <div
                                                    className={`h-2 rounded-full transition-all ${batch.status === 'on-track' ? 'bg-green-500' : 'bg-yellow-500'
                                                        }`}
                                                    style={{ width: `${batch.progress}%` }}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Commandes récentes */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Commandes récentes</h3>
                                <div className="space-y-3">
                                    {mockData.recentOrders.map(order => (
                                        <div key={order.id} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                    <p className="font-semibold text-sm">{order.id}</p>
                                                    <p className="text-xs text-gray-500">{order.customer}</p>
                                                </div>
                                                <span className={`text-xs px-2 py-1 rounded-full ${order.status === 'confirmed' ? 'bg-blue-100 text-blue-800' :
                                                        order.status === 'in_production' ? 'bg-yellow-100 text-yellow-800' :
                                                            'bg-green-100 text-green-800'
                                                    }`}>
                                                    {order.status === 'confirmed' ? 'Confirmé' :
                                                        order.status === 'in_production' ? 'Production' : 'Prêt'}
                                                </span>
                                            </div>
                                            <div className="flex justify-between items-center text-sm">
                                                <span className="text-gray-600">{order.items} poussins</span>
                                                <span className="font-semibold text-green-600">{(order.amount / 1000).toFixed(0)}K Ar</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                        </div>
                    </div>
                )}

                {/* VUE CLIENTS */}
                {activeTab === 'customers' && (
                    <div className="space-y-6">

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                            {/* Top clients */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Top 5 Clients</h3>
                                <div className="space-y-3">
                                    {mockData.topCustomers.map((customer, index) => (
                                        <div key={customer.name} className="flex items-center justify-between p-3 border-b last:border-0">
                                            <div className="flex items-center">
                                                <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold mr-3">
                                                    {index + 1}
                                                </div>
                                                <div>
                                                    <p className="font-semibold text-sm">{customer.name}</p>
                                                    <p className="text-xs text-gray-500">{customer.orders} commandes</p>
                                                </div>
                                            </div>
                                            <p className="font-semibold text-green-600">{(customer.revenue / 1000000).toFixed(1)}M Ar</p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Répartition commandes */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Répartition des commandes</h3>
                                <ResponsiveContainer width="100%" height={250}>
                                    <PieChart>
                                        <Pie
                                            data={mockData.ordersByStatus}
                                            cx="50%"
                                            cy="50%"
                                            labelLine={false}
                                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                            outerRadius={80}
                                            fill="#8884d8"
                                            dataKey="value"
                                        >
                                            {mockData.ordersByStatus.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>

                        </div>
                    </div>
                )}

                {/* VUE FOURNISSEURS */}
                {activeTab === 'suppliers' && (
                    <div className="space-y-6">

                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold mb-4">Performance Fournisseurs</h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={mockData.supplierPerformance}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                                    <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                                    <Tooltip />
                                    <Legend />
                                    <Bar dataKey="onTime" fill="#3b82f6" name="Livraison à temps (%)" />
                                    <Bar dataKey="rating" fill="#10b981" name="Note globale (x20)" />
                                </BarChart>
                            </ResponsiveContainer>

                            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {mockData.supplierPerformance.map(supplier => (
                                    <div key={supplier.name} className="border rounded-lg p-4">
                                        <p className="font-semibold text-sm mb-2">{supplier.name}</p>
                                        <div className="space-y-1 text-xs">
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Note globale:</span>
                                                <span className="font-semibold text-yellow-600">⭐ {supplier.rating}/5</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Qualité:</span>
                                                <span className="font-semibold text-green-600">{supplier.quality}/5</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Ponctualité:</span>
                                                <span className="font-semibold text-blue-600">{supplier.onTime}%</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* VUE ANALYTIQUES */}
                {activeTab === 'analytics' && (
                    <div className="space-y-6">

                        {/* KPIs détaillés */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h4 className="text-sm font-medium text-gray-600 mb-2">Coût par poussin</h4>
                                <p className="text-3xl font-bold text-blue-600">1,247 Ar</p>
                                <p className="text-xs text-green-600 mt-1">↓ -5.2% vs mois dernier</p>
                            </div>
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h4 className="text-sm font-medium text-gray-600 mb-2">Marge moyenne</h4>
                                <p className="text-3xl font-bold text-green-600">38.5%</p>
                                <p className="text-xs text-green-600 mt-1">↑ +2.1% vs mois dernier</p>
                            </div>
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h4 className="text-sm font-medium text-gray-600 mb-2">Délai moyen livraison</h4>
                                <p className="text-3xl font-bold text-orange-600">2.3 jours</p>
                                <p className="text-xs text-red-600 mt-1">↑ +0.5j vs mois dernier</p>
                            </div>
                        </div>

                        {/* Évolution production */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold mb-4">Évolution de la production</h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <AreaChart data={mockData.incubatorPerformance}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                                    <YAxis tick={{ fontSize: 12 }} />
                                    <Tooltip />
                                    <Legend />
                                    <Area type="monotone" dataKey="eggs" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} name="Œufs en incubation" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                    </div>
                )}

            </div>
        </div>
    );
};

export default IncubatorDashboard;
