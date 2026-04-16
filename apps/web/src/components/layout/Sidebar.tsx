import { Link, useLocation } from 'react-router-dom';
import {
  BarChart3,
  Upload,
  Database,
  Cpu,
  Activity,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const navItems = [
  { href: '/', icon: Upload, label: 'Upload' },
  { href: '/datasets', icon: Database, label: 'Datasets' },
  { href: '/jobs', icon: Activity, label: 'Job History' },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 bg-surface-900 text-white flex flex-col shrink-0 h-screen sticky top-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-surface-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-semibold text-sm text-white">ProcessMiner</div>
            <div className="text-xs text-surface-400">AI Process Analyzer</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active =
            item.href === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150',
                active
                  ? 'bg-primary-600 text-white'
                  : 'text-surface-300 hover:bg-surface-700 hover:text-white'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {item.label}
              {active && <ChevronRight className="w-3.5 h-3.5 ml-auto" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-surface-700">
        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-surface-400" />
          <span className="text-xs text-surface-400">Phase 1 MVP</span>
        </div>
        <p className="text-xs text-surface-500 mt-1">
          Evidence-first process intelligence
        </p>
      </div>
    </aside>
  );
}
