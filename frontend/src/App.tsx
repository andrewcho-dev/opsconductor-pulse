import { AuthProvider, useAuth } from "@/services/auth/AuthProvider";

function AppContent() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold text-primary">OpsConductor Pulse</h1>
        <p className="text-muted-foreground">Authenticated as: {user?.email}</p>
        <p className="text-sm text-muted-foreground">
          Tenant: {user?.tenantId} | Role: {user?.role}
        </p>
        <button
          onClick={logout}
          className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-accent"
        >
          Logout
        </button>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
