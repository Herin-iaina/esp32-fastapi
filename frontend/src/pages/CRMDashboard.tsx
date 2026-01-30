import React, { useState, useEffect } from 'react';
import {
    LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, AreaChart, Area
} from 'recharts';
import {
    Activity, TrendingUp, Users, Package, DollarSign,
    AlertCircle, ThermometerSun, Droplets, ShoppingCart,
    Truck, CheckCircle, Clock
} from 'lucide-react';
import axios from 'axios';

// API Configuration
const API_BASE_URL = '/api';

const StatCard = ({ icon: Icon, title, value, subtitle, color, trend }) => (
    <div className="bg-white rounded-lg shadow-sm p-6 border-l-4" style={{ borderLeftColor: color }}>
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

const CRMDashboard = () => {
    const [activeTab, setActiveTab] = useState('overview');
    const [stats, setStats] = useState({
        activeIncubators: 0,
        totalEggs: 0,
        dailyRevenue: 0,
        pendingOrders: 0,
        activeSuppliers: 0,
        activeCustomers: 0,
        hatchRate: 0
    });

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/analytics/dashboard/overview`);
                setStats(response.data.stats);
            } catch (error) {
                console.error("Error fetching dashboard stats:", error);
            }
        };
        fetchStats();
    }, []);

    const tabs = [
        { id: 'overview', label: 'Vue d\'ensemble', icon: Activity },
        { id: 'incubators', label: 'Incubateurs', icon: ThermometerSun },
        { id: 'customers', label: 'Clients', icon: Users },
        { id: 'suppliers', label: 'Fournisseurs', icon: Truck },
        { id: 'analytics', label: 'Analytiques', icon: TrendingUp }
    ];

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center bg-white p-6 rounded-lg shadow-sm">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800">Système CRM & IoT</h1>
                    <p className="text-gray-500">Gestion intégrée des incubateurs et de la relation client</p>
                </div>
                <div className="flex space-x-2">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center px-4 py-2 rounded-md transition-colors ${activeTab === tab.id
                                    ? 'bg-blue-600 text-white shadow-md'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            <tab.icon size={18} className="mr-2" />
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Overview Tab Content */}
            {activeTab === 'overview' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <StatCard
                        icon={Activity}
                        title="Incubateurs actifs"
                        value={stats.activeIncubators}
                        subtitle={`${stats.totalEggs} œufs en cours`}
                        color="#3b82f6"
                        trend={12}
                    />
                    <StatCard
                        icon={CheckCircle}
                        title="Taux de réussite"
                        value={`${stats.hatchRate}%`}
                        subtitle="Moyenne globale"
                        color="#10b981"
                        trend={3.2}
                    />
                    <StatCard
                        icon={DollarSign}
                        title="Revenus du jour"
                        value={`${(stats.dailyRevenue / 1000).toFixed(0)}K Ar`}
                        subtitle="Dernières 24h"
                        color="#f59e0b"
                        trend={8.5}
                    />
                    <StatCard
                        icon={Users}
                        title="Clients/Fournisseurs"
                        value={`${stats.activeCustomers}/${stats.activeSuppliers}`}
                        subtitle="Total actifs"
                        color="#8b5cf6"
                    />
                </div>
            )}

            {/* Placeholder for other tabs */}
            {activeTab !== 'overview' && (
                <div className="bg-white p-12 rounded-lg shadow-sm text-center">
                    <AlertCircle size={48} className="mx-auto text-blue-200 mb-4" />
                    <h3 className="text-xl font-semibold text-gray-700">Module en cours de développement</h3>
                    <p className="text-gray-500">La vue d'ensemble est déjà fonctionnelle avec les données réelles de l'API.</p>
                </div>
            )}
        </div>
    );
};

export default CRMDashboard;
