import { createBrowserRouter, Link, Navigate, type RouteObject } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ProtectedLayout } from './AppShell';
import { LoginPage } from '@/features/auth/LoginPage';
import { HomePage } from '@/features/home/HomePage';
import { EmptyState } from '@/components/ui';
import { featurePaths } from './feature-routes';
import { registerLocales } from '@/i18n';
for (const [path, module] of Object.entries(import.meta.glob<{ locales: { en: object; es: object } }>('../features/*/locales.ts', { eager: true }))) registerLocales(path.split('/').at(-2)!, module.locales);
const featureLoaders = import.meta.glob<{ routes: RouteObject[] }>('../features/*/routes.tsx');
const featureRoutes: RouteObject[] = Object.entries(featurePaths).flatMap(([feature, paths]) => paths.map(path => ({ path, lazy: async () => {
 const loader = featureLoaders[`../features/${feature}/routes.tsx`];
 if (!loader) throw new Error('Route module is unavailable');
 const module = await loader();
 const route = module.routes.find(item => item.path?.replace(/^\//, '') === path);
 if (!route) throw new Error('Route definition is unavailable');
 return { Component: route.Component, element: route.element };
} })));

function MissingPage() { const { t } = useTranslation(); return <EmptyState title={t('missingTitle')} description={t('missingDescription')} action={<Link to="/inicio">{t('home')}</Link>}/>; }
function RouteFailure() { const { t } = useTranslation(); return <EmptyState title={t('errors.failed')} action={<Link to="/inicio">{t('home')}</Link>}/>; }
export const routes: RouteObject[] = [
 { path:'/entrar',element:<LoginPage/> },
 { path:'/',element:<ProtectedLayout/>,errorElement:<RouteFailure/>,children:[ { index:true,element:<Navigate to="/inicio" replace/> }, { path:'/inicio',element:<HomePage/> }, ...featureRoutes, { path:'*',element:<MissingPage/> } ] },
];
export const router = createBrowserRouter(routes);
