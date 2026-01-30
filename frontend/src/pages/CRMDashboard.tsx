import { useState, useEffect } from 'react';
import {
    LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, AreaChart, Area
} from 'recharts';
import {
    Activity, TrendingUp, Users, DollarSign,
    AlertCircle, ThermometerSun, Droplets,
    Truck, CheckCircle, TrendingDown
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = '/api';

// Types
interface Stats {
    activeIncubators: number;
    totalEggs: number;
    dailyRevenue: number;
    dailyOrdersCount: number;
    pendingOrders: number;
    activeSuppliers: number;
    activeCustomers: number;
    hatchRate: number;
    currentTemperature: number;
    currentHumidity: number;
    targetTemperature: number;
    targetHumidity: number;
    daysRemaining: number;
    currentDay: number;
    totalDays: number;
    species: string;
}

interface IncubatorData {
    date: string;
    temp: number;
    humidity: number;
}

interface RevenueData {
    month: string;
    revenue: number;
    costs: number;
}

interface OrderStatus {
    name: string;
    value: number;
    color: string;
}

interface Customer {
    name: string;
    orders: number;
    revenue: number;
}

interface Supplier {
    name: string;
    rating: number;
    onTime: number;
    quality: number;
}

interface Order {
    id: string;
    customer: string;
    amount: number;
    status: string;
    statusLabel: string;
    date: string;
}

interface Batch {
    id: string;
    incubator: string;
    eggs: number;
    day: number;
    totalDays: number;
    progress: number;
    status: string;
    species: string;
}

interface KPIs {
    costPerChick: number;
    costPerChickTrend: number;
    averageMargin: number;
    marginTrend: number;
    avgDeliveryDays: number;
    deliveryTrend: number;
}

// Composant carte statistique
interface StatCardProps {
    icon: any;
    title: string;
    value: string | number;
    subtitle?: string;
    color: string;
    trend?: number;
}

const StatCard = ({ icon: Icon, title, value, subtitle, color, trend }: StatCardProps) => (
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
        {trend !== undefined && (
            <div className="mt-3 flex items-center text-sm">
                {trend >= 0 ? (
                    <TrendingUp size={16} className="text-green-500" />
                ) : (
                    <TrendingDown size={16} className="text-red-500" />
                )}
                <span className={`ml-1 font-medium ${trend >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {trend >= 0 ? '+' : ''}{trend}%
                </span>
                <span className="ml-1 text-gray-500">vs mois dernier</span>
            </div>
        )}
    </div>
);

const CRMDashboard = () => {
    const [activeTab, setActiveTab] = useState('overview');
    const [loading, setLoading] = useState(true);

    // State pour toutes les données
    const [stats, setStats] = useState<Stats>({
        activeIncubators: 0,
        totalEggs: 0,
        dailyRevenue: 0,
        dailyOrdersCount: 0,
        pendingOrders: 0,
        activeSuppliers: 0,
        activeCustomers: 0,
        hatchRate: 0,
        currentTemperature: 0,
        currentHumidity: 0,
        targetTemperature: 37.5,
        targetHumidity: 60.0,
        daysRemaining: 0,
        currentDay: 0,
        totalDays: 21,
        species: 'N/A'
    });

    const [incubatorData, setIncubatorData] = useState<IncubatorData[]>([]);
    const [revenueData, setRevenueData] = useState<RevenueData[]>([]);
    const [ordersByStatus, setOrdersByStatus] = useState<OrderStatus[]>([]);
    const [topCustomers, setTopCustomers] = useState<Customer[]>([]);
    const [suppliers, setSuppliers] = useState<Supplier[]>([]);
    const [recentOrders, setRecentOrders] = useState<Order[]>([]);
    const [activeBatches, setActiveBatches] = useState<Batch[]>([]);
    const [kpis, setKpis] = useState<KPIs>({
        costPerChick: 0,
        costPerChickTrend: 0,
        averageMargin: 0,
        marginTrend: 0,
        avgDeliveryDays: 0,
        deliveryTrend: 0
    });

    // Charger les données
    useEffect(() => {
        const fetchAllData = async () => {
            setLoading(true);
            try {
                const [
                    statsRes,
                    incubatorRes,
                    revenueRes,
                    ordersStatusRes,
                    customersRes,
                    suppliersRes,
                    ordersRes,
                    batchesRes,
                    kpisRes
                ] = await Promise.all([
                    axios.get(`${API_BASE_URL}/analytics/dashboard/overview`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/incubator-performance`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/monthly-revenue`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/orders-by-status`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/top-customers`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/supplier-performance`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/recent-orders`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/active-batches`),
                    axios.get(`${API_BASE_URL}/analytics/dashboard/kpis`)
                ]);

                setStats(statsRes.data.stats);
                setIncubatorData(incubatorRes.data.data);
                setRevenueData(revenueRes.data.data);
                setOrdersByStatus(ordersStatusRes.data.data);
                setTopCustomers(customersRes.data.data);
                setSuppliers(suppliersRes.data.data);
                setRecentOrders(ordersRes.data.data);
                setActiveBatches(batchesRes.data.data);
                setKpis(kpisRes.data);
            } catch (error) {
                console.error("Error fetching dashboard data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchAllData();
        const interval = setInterval(fetchAllData, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    const tabs = [
        { id: 'overview', label: "Vue d'ensemble", icon: Activity },
        { id: 'incubators', label: 'Incubateurs', icon: ThermometerSun },
        { id: 'customers', label: 'Clients', icon: Users },
        { id: 'suppliers', label: 'Fournisseurs', icon: Truck },
        { id: 'analytics', label: 'Analytiques', icon: TrendingUp }
    ];

    if (loading && !stats.activeIncubators) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Chargement du dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
                <div className="max-w-7xl mx-auto px-6 py-6">
                    <h1 className="text-3xl font-bold">Incubateur Management System</h1>
                    <p className="text-blue-100 mt-1">Tableau de bord integre - IoT & CRM</p>
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
                                    className={`flex items-center py-4 px-2 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
                                        activeTab === tab.id
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
                                title="Capteurs actifs"
                                value={stats.activeIncubators}
                                subtitle={`${stats.totalEggs} oeufs en cours`}
                                color="#3b82f6"
                                trend={12}
                            />
                            <StatCard
                                icon={CheckCircle}
                                title="Taux de reussite moyen"
                                value={`${stats.hatchRate}%`}
                                subtitle="Ce mois-ci"
                                color="#10b981"
                                trend={3.2}
                            />
                            <StatCard
                                icon={DollarSign}
                                title="Revenus aujourd'hui"
                                value={`${(stats.dailyRevenue / 1000).toFixed(0)}K Ar`}
                                subtitle={`${stats.dailyOrdersCount} commandes`}
                                color="#f59e0b"
                                trend={8.5}
                            />
                            <StatCard
                                icon={Users}
                                title="Clients actifs"
                                value={stats.activeCustomers}
                                subtitle={`${stats.activeSuppliers} fournisseurs`}
                                color="#8b5cf6"
                            />
                        </div>

                        {/* Graphiques principaux */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Performance temperature/humidite */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center">
                                    <ThermometerSun className="mr-2 text-orange-500" size={20} />
                                    Conditions d'incubation (7 jours)
                                </h3>
                                <ResponsiveContainer width="100%" height={250}>
                                    <LineChart data={incubatorData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                                        <YAxis yAxisId="left" domain={[35, 40]} tick={{ fontSize: 12 }} />
                                        <YAxis yAxisId="right" orientation="right" domain={[50, 80]} tick={{ fontSize: 12 }} />
                                        <Tooltip />
                                        <Legend />
                                        <Line yAxisId="left" type="monotone" dataKey="temp" stroke="#f59e0b" strokeWidth={2} name="Temperature (C)" dot={false} />
                                        <Line yAxisId="right" type="monotone" dataKey="humidity" stroke="#3b82f6" strokeWidth={2} name="Humidite (%)" dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Revenus vs Couts */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center">
                                    <DollarSign className="mr-2 text-green-500" size={20} />
                                    Revenus vs Couts (7 mois)
                                </h3>
                                <ResponsiveContainer width="100%" height={250}>
                                    <AreaChart data={revenueData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                        <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                                        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
                                        <Tooltip formatter={(value: number) => `${(value / 1000000).toFixed(2)}M Ar`} />
                                        <Legend />
                                        <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="#10b981" fillOpacity={0.6} name="Revenus" />
                                        <Area type="monotone" dataKey="costs" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} name="Couts" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Lots actifs et commandes recentes */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Lots en cours */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Lots d'incubation actifs</h3>
                                {activeBatches.length > 0 ? (
                                    <div className="space-y-3">
                                        {activeBatches.map(batch => (
                                            <div key={batch.id} className="border rounded-lg p-4">
                                                <div className="flex justify-between items-start mb-2">
                                                    <div>
                                                        <p className="font-semibold text-sm">{batch.id}</p>
                                                        <p className="text-xs text-gray-500">{batch.incubator} - {batch.eggs} oeufs - {batch.species}</p>
                                                    </div>
                                                    <span className={`text-xs px-2 py-1 rounded-full ${
                                                        batch.status === 'on-track' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                                                    }`}>
                                                        Jour {batch.day}/{batch.totalDays}
                                                    </span>
                                                </div>
                                                <div className="w-full bg-gray-200 rounded-full h-2">
                                                    <div
                                                        className={`h-2 rounded-full transition-all ${
                                                            batch.status === 'on-track' ? 'bg-green-500' : 'bg-yellow-500'
                                                        }`}
                                                        style={{ width: `${batch.progress}%` }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-8 text-gray-500">
                                        <AlertCircle className="mx-auto mb-2" size={32} />
                                        <p>Aucun lot actif</p>
                                    </div>
                                )}
                            </div>

                            {/* Commandes recentes */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Commandes recentes</h3>
                                {recentOrders.length > 0 ? (
                                    <div className="space-y-3">
                                        {recentOrders.map(order => (
                                            <div key={order.id} className="border rounded-lg p-4">
                                                <div className="flex justify-between items-start mb-2">
                                                    <div>
                                                        <p className="font-semibold text-sm">{order.id}</p>
                                                        <p className="text-xs text-gray-500">{order.customer}</p>
                                                    </div>
                                                    <span className={`text-xs px-2 py-1 rounded-full ${
                                                        order.status === 'confirmed' ? 'bg-blue-100 text-blue-800' :
                                                        order.status === 'in_production' ? 'bg-yellow-100 text-yellow-800' :
                                                        order.status === 'ready' ? 'bg-green-100 text-green-800' :
                                                        order.status === 'pending' ? 'bg-orange-100 text-orange-800' :
                                                        'bg-gray-100 text-gray-800'
                                                    }`}>
                                                        {order.statusLabel}
                                                    </span>
                                                </div>
                                                <div className="flex justify-between items-center text-sm">
                                                    <span className="text-gray-600">{order.date}</span>
                                                    <span className="font-semibold text-green-600">{(order.amount / 1000).toFixed(0)}K Ar</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-8 text-gray-500">
                                        <AlertCircle className="mx-auto mb-2" size={32} />
                                        <p>Aucune commande recente</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* VUE INCUBATEURS */}
                {activeTab === 'incubators' && (
                    <div className="space-y-6">
                        {/* Stats incubation */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            <StatCard
                                icon={ThermometerSun}
                                title="Temperature actuelle"
                                value={`${stats.currentTemperature?.toFixed(1) || 0}C`}
                                subtitle={`Cible: ${stats.targetTemperature}C`}
                                color="#ef4444"
                            />
                            <StatCard
                                icon={Droplets}
                                title="Humidite actuelle"
                                value={`${stats.currentHumidity?.toFixed(1) || 0}%`}
                                subtitle={`Cible: ${stats.targetHumidity}%`}
                                color="#3b82f6"
                            />
                            <StatCard
                                icon={Activity}
                                title="Jour d'incubation"
                                value={`${stats.currentDay}/${stats.totalDays}`}
                                subtitle={`${stats.daysRemaining} jours restants`}
                                color="#10b981"
                            />
                            <StatCard
                                icon={CheckCircle}
                                title="Espece"
                                value={stats.species}
                                subtitle="En cours d'incubation"
                                color="#8b5cf6"
                            />
                        </div>

                        {/* Graphique temperature/humidite */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold mb-4">Historique des conditions</h3>
                            <ResponsiveContainer width="100%" height={350}>
                                <LineChart data={incubatorData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                                    <YAxis yAxisId="left" domain={[35, 40]} tick={{ fontSize: 12 }} label={{ value: 'Temp (C)', angle: -90, position: 'insideLeft' }} />
                                    <YAxis yAxisId="right" orientation="right" domain={[50, 80]} tick={{ fontSize: 12 }} label={{ value: 'Humidite (%)', angle: 90, position: 'insideRight' }} />
                                    <Tooltip />
                                    <Legend />
                                    <Line yAxisId="left" type="monotone" dataKey="temp" stroke="#f59e0b" strokeWidth={2} name="Temperature" />
                                    <Line yAxisId="right" type="monotone" dataKey="humidity" stroke="#3b82f6" strokeWidth={2} name="Humidite" />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Liste des lots */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold mb-4">Lots en cours</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {activeBatches.map(batch => (
                                    <div key={batch.id} className="border rounded-lg p-4">
                                        <div className="flex justify-between items-start mb-3">
                                            <div>
                                                <p className="font-bold text-lg">{batch.id}</p>
                                                <p className="text-sm text-gray-500">{batch.incubator}</p>
                                            </div>
                                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                                                batch.status === 'on-track' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                                            }`}>
                                                {batch.status === 'on-track' ? 'En cours' : 'Attention'}
                                            </span>
                                        </div>
                                        <div className="grid grid-cols-3 gap-2 text-center mb-3">
                                            <div>
                                                <p className="text-2xl font-bold text-blue-600">{batch.eggs}</p>
                                                <p className="text-xs text-gray-500">Oeufs</p>
                                            </div>
                                            <div>
                                                <p className="text-2xl font-bold text-orange-600">{batch.day}</p>
                                                <p className="text-xs text-gray-500">Jour</p>
                                            </div>
                                            <div>
                                                <p className="text-2xl font-bold text-green-600">{batch.progress}%</p>
                                                <p className="text-xs text-gray-500">Progress</p>
                                            </div>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-3">
                                            <div
                                                className={`h-3 rounded-full ${batch.status === 'on-track' ? 'bg-green-500' : 'bg-yellow-500'}`}
                                                style={{ width: `${batch.progress}%` }}
                                            />
                                        </div>
                                        <p className="text-xs text-gray-500 mt-2 text-center">Espece: {batch.species}</p>
                                    </div>
                                ))}
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
                                {topCustomers.length > 0 ? (
                                    <div className="space-y-3">
                                        {topCustomers.map((customer, index) => (
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
                                ) : (
                                    <div className="text-center py-8 text-gray-500">
                                        <Users className="mx-auto mb-2" size={32} />
                                        <p>Aucun client enregistre</p>
                                    </div>
                                )}
                            </div>

                            {/* Repartition commandes */}
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Repartition des commandes</h3>
                                {ordersByStatus.length > 0 && ordersByStatus.some(o => o.value > 0) ? (
                                    <ResponsiveContainer width="100%" height={250}>
                                        <PieChart>
                                            <Pie
                                                data={ordersByStatus}
                                                cx="50%"
                                                cy="50%"
                                                labelLine={false}
                                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                                outerRadius={80}
                                                fill="#8884d8"
                                                dataKey="value"
                                            >
                                                {ordersByStatus.map((entry, index) => (
                                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                                ))}
                                            </Pie>
                                            <Tooltip />
                                        </PieChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="text-center py-8 text-gray-500">
                                        <AlertCircle className="mx-auto mb-2" size={32} />
                                        <p>Aucune commande</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Liste des commandes */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold mb-4">Commandes recentes</h3>
                            <div className="overflow-x-auto">
                                <table className="min-w-full">
                                    <thead>
                                        <tr className="border-b">
                                            <th className="text-left py-3 px-4 font-semibold text-gray-600">ID</th>
                                            <th className="text-left py-3 px-4 font-semibold text-gray-600">Client</th>
                                            <th className="text-left py-3 px-4 font-semibold text-gray-600">Date</th>
                                            <th className="text-left py-3 px-4 font-semibold text-gray-600">Statut</th>
                                            <th className="text-right py-3 px-4 font-semibold text-gray-600">Montant</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recentOrders.map(order => (
                                            <tr key={order.id} className="border-b hover:bg-gray-50">
                                                <td className="py-3 px-4 font-medium">{order.id}</td>
                                                <td className="py-3 px-4">{order.customer}</td>
                                                <td className="py-3 px-4 text-gray-500">{order.date}</td>
                                                <td className="py-3 px-4">
                                                    <span className={`px-2 py-1 rounded-full text-xs ${
                                                        order.status === 'confirmed' ? 'bg-blue-100 text-blue-800' :
                                                        order.status === 'in_production' ? 'bg-yellow-100 text-yellow-800' :
                                                        order.status === 'ready' ? 'bg-green-100 text-green-800' :
                                                        order.status === 'pending' ? 'bg-orange-100 text-orange-800' :
                                                        'bg-gray-100 text-gray-800'
                                                    }`}>
                                                        {order.statusLabel}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4 text-right font-semibold text-green-600">
                                                    {(order.amount / 1000).toFixed(0)}K Ar
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}

                {/* VUE FOURNISSEURS */}
                {activeTab === 'suppliers' && (
                    <div className="space-y-6">
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold mb-4">Performance Fournisseurs</h3>
                            {suppliers.length > 0 ? (
                                <>
                                    <ResponsiveContainer width="100%" height={300}>
                                        <BarChart data={suppliers}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                                            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                                            <Tooltip />
                                            <Legend />
                                            <Bar dataKey="onTime" fill="#3b82f6" name="Livraison a temps (%)" />
                                            <Bar dataKey="quality" fill="#10b981" name="Qualite (x20)" />
                                        </BarChart>
                                    </ResponsiveContainer>

                                    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                        {suppliers.map(supplier => (
                                            <div key={supplier.name} className="border rounded-lg p-4">
                                                <p className="font-semibold text-sm mb-2">{supplier.name}</p>
                                                <div className="space-y-1 text-xs">
                                                    <div className="flex justify-between">
                                                        <span className="text-gray-600">Note globale:</span>
                                                        <span className="font-semibold text-yellow-600">{supplier.rating}/5</span>
                                                    </div>
                                                    <div className="flex justify-between">
                                                        <span className="text-gray-600">Qualite:</span>
                                                        <span className="font-semibold text-green-600">{supplier.quality}/5</span>
                                                    </div>
                                                    <div className="flex justify-between">
                                                        <span className="text-gray-600">Ponctualite:</span>
                                                        <span className="font-semibold text-blue-600">{supplier.onTime}%</span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            ) : (
                                <div className="text-center py-12 text-gray-500">
                                    <Truck className="mx-auto mb-2" size={48} />
                                    <p>Aucun fournisseur enregistre</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* VUE ANALYTIQUES */}
                {activeTab === 'analytics' && (
                    <div className="space-y-6">
                        {/* KPIs detailles */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h4 className="text-sm font-medium text-gray-600 mb-2">Cout par poussin</h4>
                                <p className="text-3xl font-bold text-blue-600">{kpis.costPerChick} Ar</p>
                                <p className={`text-xs mt-1 ${kpis.costPerChickTrend < 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {kpis.costPerChickTrend < 0 ? '↓' : '↑'} {Math.abs(kpis.costPerChickTrend)}% vs mois dernier
                                </p>
                            </div>
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h4 className="text-sm font-medium text-gray-600 mb-2">Marge moyenne</h4>
                                <p className="text-3xl font-bold text-green-600">{kpis.averageMargin}%</p>
                                <p className={`text-xs mt-1 ${kpis.marginTrend > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {kpis.marginTrend > 0 ? '↑' : '↓'} +{kpis.marginTrend}% vs mois dernier
                                </p>
                            </div>
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h4 className="text-sm font-medium text-gray-600 mb-2">Delai moyen livraison</h4>
                                <p className="text-3xl font-bold text-orange-600">{kpis.avgDeliveryDays} jours</p>
                                <p className={`text-xs mt-1 ${kpis.deliveryTrend > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                    {kpis.deliveryTrend > 0 ? '↑' : '↓'} +{kpis.deliveryTrend}j vs mois dernier
                                </p>
                            </div>
                        </div>

                        {/* Evolution production */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold mb-4">Evolution des revenus</h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <AreaChart data={revenueData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                                    <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
                                    <Tooltip formatter={(value: number) => `${(value / 1000000).toFixed(2)}M Ar`} />
                                    <Legend />
                                    <Area type="monotone" dataKey="revenue" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} name="Revenus" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Statistiques globales */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Resume activite</h3>
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Total clients</span>
                                        <span className="font-bold text-xl">{stats.activeCustomers}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Total fournisseurs</span>
                                        <span className="font-bold text-xl">{stats.activeSuppliers}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Commandes en attente</span>
                                        <span className="font-bold text-xl text-orange-600">{stats.pendingOrders}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Taux de reussite</span>
                                        <span className="font-bold text-xl text-green-600">{stats.hatchRate}%</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold mb-4">Incubation en cours</h3>
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Capteurs actifs</span>
                                        <span className="font-bold text-xl">{stats.activeIncubators}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Oeufs en incubation</span>
                                        <span className="font-bold text-xl">{stats.totalEggs}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Temperature moyenne</span>
                                        <span className="font-bold text-xl text-orange-600">{stats.currentTemperature?.toFixed(1) || 0}C</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Humidite moyenne</span>
                                        <span className="font-bold text-xl text-blue-600">{stats.currentHumidity?.toFixed(1) || 0}%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CRMDashboard;
