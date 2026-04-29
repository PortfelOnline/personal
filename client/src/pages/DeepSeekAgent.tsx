import { useState, useEffect } from 'react';
import { trpc } from '@/lib/trpc';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Loader2, Server, Activity, Key, Copy, Trash2, RefreshCw, ExternalLink, CheckCircle, XCircle, AlertCircle, Wrench } from 'lucide-react';
import { toast } from 'sonner';
import DashboardLayout from '@/components/DashboardLayout';

export default function DeepSeekAgent() {
  const [tab, setTab] = useState<'overview' | 'tools' | 'keys'>('overview');

  const health = trpc.deepseek.health.useQuery(undefined, { refetchInterval: 30_000 });
  const tools = trpc.deepseek.tools.useQuery(undefined, { refetchInterval: 60_000 });
  const tasks = trpc.deepseek.tasks.useQuery(undefined, { refetchInterval: 30_000 });
  const { data: apiKeys, refetch: refetchKeys } = trpc.deepseek.listApiKeys.useQuery();
  const createKey = trpc.deepseek.createApiKey.useMutation();
  const revokeKey = trpc.deepseek.revokeApiKey.useMutation();

  const [newKeyName, setNewKeyName] = useState('');
  const [searchTools, setSearchTools] = useState('');
  const [loadingCreate, setLoadingCreate] = useState(false);

  const healthStatus = health.data?.status as string | undefined;
  const healthOk = healthStatus === 'ok' || healthStatus === 'healthy';

  const filteredTools = (tools.data ?? []).filter((t: string) =>
    t.toLowerCase().includes(searchTools.toLowerCase())
  );

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return;
    setLoadingCreate(true);
    try {
      const result = await createKey.mutateAsync({ name: newKeyName.trim() });
      await navigator.clipboard.writeText(result.key);
      toast.success('Key created and copied to clipboard');
      setNewKeyName('');
      refetchKeys();
    } catch (err: any) {
      toast.error(err.message);
    }
    setLoadingCreate(false);
  };

  const handleRevokeKey = async (keyPrefix: string) => {
    if (!confirm(`Revoke key "${keyPrefix}"? This cannot be undone.`)) return;
    try {
      await revokeKey.mutateAsync({ key: keyPrefix });
      toast.success('Key revoked');
      refetchKeys();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 p-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Server className="h-6 w-6 text-primary" />
            <div>
              <h1 className="text-2xl font-bold tracking-tight">DeepSeek Agent</h1>
              <p className="text-sm text-muted-foreground">
                167.86.116.15:8766 · Contabo
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { health.refetch(); tools.refetch(); tasks.refetch(); refetchKeys(); }}
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        </div>

        {/* Health card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-muted-foreground" />
                <CardTitle className="text-lg">Agent Status</CardTitle>
              </div>
              <Badge variant={healthOk ? 'default' : 'destructive'} className="text-xs">
                {health.data ? (
                  <span className="flex items-center gap-1">
                    {healthOk ? <CheckCircle className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                    {healthStatus ?? JSON.stringify(health.data)}
                  </span>
                ) : health.isError ? (
                  <span className="flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    unreachable
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    loading
                  </span>
                )}
              </Badge>
            </div>
            <CardDescription>
              {health.data && (health.data as any).uptime
                ? `Uptime: ${(health.data as any).uptime}`
                : health.isError
                ? 'Cannot reach the agent server'
                : 'Checking agent health...'}
            </CardDescription>
          </CardHeader>
        </Card>

        <Tabs value={tab} onValueChange={(v) => setTab(v as any)}>
          <TabsList>
            <TabsTrigger value="overview">
              <Server className="h-4 w-4 mr-1" /> Overview
            </TabsTrigger>
            <TabsTrigger value="tools">
              <Wrench className="h-4 w-4 mr-1" /> Tools ({tools.data?.length ?? 0})
            </TabsTrigger>
            <TabsTrigger value="keys">
              <Key className="h-4 w-4 mr-1" /> API Keys ({apiKeys?.length ?? 0})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 mt-4">
            {/* Tasks */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Scheduled Tasks</CardTitle>
              </CardHeader>
              <CardContent>
                {tasks.isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : tasks.data ? (
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-64">
                    {JSON.stringify(tasks.data, null, 2)}
                  </pre>
                ) : (
                  <p className="text-sm text-muted-foreground">No tasks data</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tools" className="space-y-4 mt-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Registered Tools</CardTitle>
                  <span className="text-sm text-muted-foreground">{tools.data?.length ?? 0} total</span>
                </div>
                <CardDescription>Agent tools available for task execution</CardDescription>
              </CardHeader>
              <CardContent>
                <Input
                  placeholder="Search tools..."
                  value={searchTools}
                  onChange={(e) => setSearchTools(e.target.value)}
                  className="mb-4"
                />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 max-h-96 overflow-y-auto">
                  {filteredTools.map((tool: string) => (
                    <div key={tool} className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-md text-xs font-mono">
                      <Wrench className="h-3 w-3 shrink-0 text-muted-foreground" />
                      {tool}
                    </div>
                  ))}
                  {filteredTools.length === 0 && !tools.isLoading && (
                    <p className="text-sm text-muted-foreground col-span-full">No tools found</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="keys" className="space-y-4 mt-4">
            {/* Create key */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Create API Key</CardTitle>
                <CardDescription>New key will be copied to clipboard automatically</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Input
                    placeholder="Key name (e.g. admin, dev-user)"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateKey()}
                  />
                  <Button onClick={handleCreateKey} disabled={loadingCreate || !newKeyName.trim()}>
                    {loadingCreate ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Key className="h-4 w-4 mr-1" />}
                    Create
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Keys list */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Active Keys</CardTitle>
              </CardHeader>
              <CardContent>
                {apiKeys?.length ? (
                  <div className="space-y-2">
                    {apiKeys.map((k: any) => (
                      <div key={k.prefix} className="flex items-center justify-between p-3 bg-muted rounded-md">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm">{k.prefix}</span>
                            <Badge variant="outline" className="text-xs">{k.role}</Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {k.name} · created {k.created_at?.slice(0, 10)}
                            {k.last_used_at ? ` · last used ${k.last_used_at?.slice(0, 10)}` : ''}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRevokeKey(k.prefix)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {apiKeys === undefined ? 'Loading...' : 'No API keys yet'}
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
