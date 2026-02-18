export interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
  subcategories?: Subcategory[];
}

export interface Subcategory {
  id: string;
  name: string;
  categoryId: string;
}

export interface Transaction {
  id: string;
  amount: number;
  description: string;
  date: string;
  categoryId: string;
  subcategoryId?: string;
  merchantId: string;
}

export interface Merchant {
  id: string;
  name: string;
  defaultCategoryId?: string;
  defaultSubcategoryId?: string;
}

export interface Budget {
  id: string;
  categoryId: string;
  amount: number;
  period: 'monthly' | 'weekly' | 'yearly';
  spent: number;
}

export interface MerchantRule {
  id: string;
  merchantId: string;
  categoryId: string;
  subcategoryId?: string;
}

export const categories: Category[] = [
  {
    id: '1',
    name: 'Alimentación',
    icon: '🍔',
    color: '#10b981',
    subcategories: [
      { id: 's1', name: 'Supermercado', categoryId: '1' },
      { id: 's2', name: 'Restaurantes', categoryId: '1' },
      { id: 's3', name: 'Delivery', categoryId: '1' },
    ],
  },
  {
    id: '2',
    name: 'Transporte',
    icon: '🚗',
    color: '#3b82f6',
    subcategories: [
      { id: 's4', name: 'Combustible', categoryId: '2' },
      { id: 's5', name: 'Transporte público', categoryId: '2' },
      { id: 's6', name: 'Uber/Taxi', categoryId: '2' },
    ],
  },
  {
    id: '3',
    name: 'Entretenimiento',
    icon: '🎬',
    color: '#8b5cf6',
    subcategories: [
      { id: 's7', name: 'Streaming', categoryId: '3' },
      { id: 's8', name: 'Cine', categoryId: '3' },
      { id: 's9', name: 'Eventos', categoryId: '3' },
    ],
  },
  {
    id: '4',
    name: 'Salud',
    icon: '⚕️',
    color: '#ef4444',
    subcategories: [
      { id: 's10', name: 'Farmacia', categoryId: '4' },
      { id: 's11', name: 'Médico', categoryId: '4' },
      { id: 's12', name: 'Gimnasio', categoryId: '4' },
    ],
  },
  {
    id: '5',
    name: 'Compras',
    icon: '🛍️',
    color: '#f59e0b',
    subcategories: [
      { id: 's13', name: 'Ropa', categoryId: '5' },
      { id: 's14', name: 'Electrónica', categoryId: '5' },
      { id: 's15', name: 'Hogar', categoryId: '5' },
    ],
  },
  {
    id: '6',
    name: 'Servicios',
    icon: '💡',
    color: '#06b6d4',
    subcategories: [
      { id: 's16', name: 'Electricidad', categoryId: '6' },
      { id: 's17', name: 'Internet', categoryId: '6' },
      { id: 's18', name: 'Agua', categoryId: '6' },
    ],
  },
];

export const merchants: Merchant[] = [
  { id: 'm1', name: 'Walmart', defaultCategoryId: '1' },
  { id: 'm2', name: 'Starbucks', defaultCategoryId: '1' },
  { id: 'm3', name: 'Shell', defaultCategoryId: '2' },
  { id: 'm4', name: 'Uber', defaultCategoryId: '2' },
  { id: 'm5', name: 'Netflix', defaultCategoryId: '3' },
  { id: 'm6', name: 'Spotify', defaultCategoryId: '3' },
  { id: 'm7', name: 'Farmacia del Ahorro', defaultCategoryId: '4' },
  { id: 'm8', name: 'Amazon', defaultCategoryId: '5' },
  { id: 'm9', name: 'CFE', defaultCategoryId: '6' },
  { id: 'm10', name: 'Totalplay', defaultCategoryId: '6' },
];

export const transactions: Transaction[] = [
  {
    id: 't1',
    amount: -1250.50,
    description: 'Compra semanal',
    date: '2026-02-12',
    categoryId: '1',
    subcategoryId: 's1',
    merchantId: 'm1',
  },
  {
    id: 't2',
    amount: -85.00,
    description: 'Café y desayuno',
    date: '2026-02-12',
    categoryId: '1',
    subcategoryId: 's2',
    merchantId: 'm2',
  },
  {
    id: 't3',
    amount: -650.00,
    description: 'Gasolina',
    date: '2026-02-11',
    categoryId: '2',
    subcategoryId: 's4',
    merchantId: 'm3',
  },
  {
    id: 't4',
    amount: -125.00,
    description: 'Viaje al trabajo',
    date: '2026-02-11',
    categoryId: '2',
    subcategoryId: 's6',
    merchantId: 'm4',
  },
  {
    id: 't5',
    amount: -279.00,
    description: 'Suscripción mensual',
    date: '2026-02-10',
    categoryId: '3',
    subcategoryId: 's7',
    merchantId: 'm5',
  },
  {
    id: 't6',
    amount: -165.00,
    description: 'Suscripción mensual',
    date: '2026-02-10',
    categoryId: '3',
    subcategoryId: 's7',
    merchantId: 'm6',
  },
  {
    id: 't7',
    amount: -450.00,
    description: 'Medicamentos',
    date: '2026-02-09',
    categoryId: '4',
    subcategoryId: 's10',
    merchantId: 'm7',
  },
  {
    id: 't8',
    amount: -1899.00,
    description: 'Audífonos Bluetooth',
    date: '2026-02-08',
    categoryId: '5',
    subcategoryId: 's14',
    merchantId: 'm8',
  },
  {
    id: 't9',
    amount: -850.00,
    description: 'Recibo de luz',
    date: '2026-02-07',
    categoryId: '6',
    subcategoryId: 's16',
    merchantId: 'm9',
  },
  {
    id: 't10',
    amount: -599.00,
    description: 'Internet fibra óptica',
    date: '2026-02-06',
    categoryId: '6',
    subcategoryId: 's17',
    merchantId: 'm10',
  },
  {
    id: 't11',
    amount: -320.00,
    description: 'Comida delivery',
    date: '2026-02-06',
    categoryId: '1',
    subcategoryId: 's3',
    merchantId: 'm2',
  },
  {
    id: 't12',
    amount: -2500.00,
    description: 'Compra mensual',
    date: '2026-02-05',
    categoryId: '1',
    subcategoryId: 's1',
    merchantId: 'm1',
  },
  {
    id: 't13',
    amount: -180.00,
    description: 'Viaje al centro',
    date: '2026-02-05',
    categoryId: '2',
    subcategoryId: 's6',
    merchantId: 'm4',
  },
  {
    id: 't14',
    amount: -750.00,
    description: 'Gasolina',
    date: '2026-02-04',
    categoryId: '2',
    subcategoryId: 's4',
    merchantId: 'm3',
  },
  {
    id: 't15',
    amount: -1250.00,
    description: 'Camisa y pantalón',
    date: '2026-02-03',
    categoryId: '5',
    subcategoryId: 's13',
    merchantId: 'm8',
  },
];

export const budgets: Budget[] = [
  {
    id: 'b1',
    categoryId: '1',
    amount: 8000,
    period: 'monthly',
    spent: 4405.5,
  },
  {
    id: 'b2',
    categoryId: '2',
    amount: 3000,
    period: 'monthly',
    spent: 1705,
  },
  {
    id: 'b3',
    categoryId: '3',
    amount: 1000,
    period: 'monthly',
    spent: 444,
  },
  {
    id: 'b4',
    categoryId: '4',
    amount: 2000,
    period: 'monthly',
    spent: 450,
  },
  {
    id: 'b5',
    categoryId: '5',
    amount: 3000,
    period: 'monthly',
    spent: 3149,
  },
  {
    id: 'b6',
    categoryId: '6',
    amount: 2500,
    period: 'monthly',
    spent: 1449,
  },
];

export const merchantRules: MerchantRule[] = [
  { id: 'r1', merchantId: 'm1', categoryId: '1', subcategoryId: 's1' },
  { id: 'r2', merchantId: 'm2', categoryId: '1', subcategoryId: 's2' },
  { id: 'r3', merchantId: 'm3', categoryId: '2', subcategoryId: 's4' },
  { id: 'r4', merchantId: 'm4', categoryId: '2', subcategoryId: 's6' },
  { id: 'r5', merchantId: 'm5', categoryId: '3', subcategoryId: 's7' },
  { id: 'r6', merchantId: 'm6', categoryId: '3', subcategoryId: 's7' },
  { id: 'r7', merchantId: 'm7', categoryId: '4', subcategoryId: 's10' },
  { id: 'r8', merchantId: 'm9', categoryId: '6', subcategoryId: 's16' },
  { id: 'r9', merchantId: 'm10', categoryId: '6', subcategoryId: 's17' },
];