import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { trpc } from '@/lib/trpc';
import { useAuth } from '@/_core/hooks/useAuth';
import { Facebook, Instagram, Trash2, Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import DashboardLayout from '@/components/DashboardLayout';

export default function MetaAccounts() {
  const { user } = useAuth();
  const [oauthUrl, setOauthUrl] = useState<string>('');
  const [polling, setPolling] = useState(false);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const { data: accounts, isLoading, refetch } = trpc.meta.getAccounts.useQuery();
  const { mutate: disconnect } = trpc.meta.disconnectAccount.useMutation({
    onSuccess: () => {
      toast.success('Account disconnected');
      refetch();
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to disconnect account');
    },
  });
  const { mutate: pollPending } = trpc.meta.pollPendingAuth.useMutation({
    onSuccess: (data) => {
      if (data.ready) {
        stopPolling();
        toast.success(`Connected ${(data.instagramAccounts ?? 0) + (data.facebookPages ?? 0)} account(s)!`);
        refetch();
      }
    },
    onError: () => {
      stopPolling();
      toast.error('Failed to process Meta authorization');
    },
  });

  const { data: oauthData } = trpc.meta.getOAuthUrl.useQuery();

  useEffect(() => {
    if (oauthData?.oauthUrl) setOauthUrl(oauthData.oauthUrl);
  }, [oauthData]);

  // Clean up polling on unmount
  useEffect(() => () => stopPolling(), []);

  const stopPolling = () => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    setPolling(false);
  };

  const handleConnectMeta = () => {
    if (!oauthUrl) return;
    // Open OAuth in new tab — current page keeps polling
    window.open(oauthUrl, '_blank', 'noopener');
    setPolling(true);
    toast.info('Authorize in the new tab. This page will update automatically.');
    // Poll every 2.5 seconds for up to 5 minutes
    let attempts = 0;
    pollTimer.current = setInterval(() => {
      attempts++;
      if (attempts > 120) {
        stopPolling();
        toast.error('Timed out waiting for Meta authorization');
        return;
      }
      pollPending();
    }, 2500);
  };

  const handleDisconnect = (accountId: string) => {
    if (confirm('Are you sure you want to disconnect this account?')) {
      disconnect({ accountId });
    }
  };

  const getAccountIcon = (accountType: string) => {
    return accountType === 'instagram_business' ? (
      <Instagram className="w-5 h-5 text-pink-500" />
    ) : (
      <Facebook className="w-5 h-5 text-blue-600" />
    );
  };

  const getAccountLabel = (accountType: string) => {
    return accountType === 'instagram_business' ? 'Instagram' : 'Facebook';
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Connected Accounts</h1>
          <p className="text-slate-600">Manage your Facebook and Instagram accounts for direct posting</p>
        </div>

        {/* Connect Button */}
        <Card className="mb-8 border-2 border-dashed">
          <CardHeader>
            <CardTitle>Connect New Account</CardTitle>
            <CardDescription>Link your Facebook or Instagram account to start publishing content</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={polling ? stopPolling : handleConnectMeta}
              disabled={!oauthUrl}
              variant={polling ? 'outline' : 'default'}
              className="gap-2"
            >
              {polling ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Waiting for authorization… (cancel)
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Connect Meta Account
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Accounts List */}
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-slate-900">Your Accounts</h2>
          
          {isLoading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
              </CardContent>
            </Card>
          ) : accounts && accounts.length > 0 ? (
            <div className="grid gap-4">
              {accounts.map((account) => (
                <Card key={account.id} className="hover:shadow-lg transition-shadow">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="p-3 bg-slate-100 rounded-lg">
                          {getAccountIcon(account.accountType)}
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-900">{account.accountName}</h3>
                          <p className="text-sm text-slate-500 flex items-center gap-2">
                            <Badge variant="outline">{getAccountLabel(account.accountType)}</Badge>
                            {account.isActive ? (
                              <Badge className="bg-green-100 text-green-800">Active</Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-800">Inactive</Badge>
                            )}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDisconnect(account.accountId)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="text-center">
                  <p className="text-slate-600 mb-4">No accounts connected yet</p>
                  <p className="text-sm text-slate-500">Connect your first Meta account to start publishing</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
