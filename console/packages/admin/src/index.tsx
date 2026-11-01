/** 平台管理共享页：用户 / 租户 / 项目 / 角色（三大支撑平台共挂 /platform/*）。
 *
 * 全部经统一网关分发（platform.* 场景）；权限由后端强制，前端以 PermissionGate
 * / useScope 镜像显隐，避免无权操作的无效交互。
 */
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { PermissionGate, useScope } from "@opchub/console-ui";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  PageHeader,
  Spinner,
  cn,
} from "@opchub/console-ui";

const th = "px-4 py-2.5 text-left text-xs font-medium text-muted-foreground";
const td = "px-4 py-2.5 align-middle";

function useInvalidate() {
  const qc = useQueryClient();
  return (...keys: string[]) => {
    for (const key of keys) qc.invalidateQueries({ queryKey: [key] });
  };
}


// 治理写操作统一经 OPC_PLATFORM_GOVERNANCE_PIPELINE（MicroFlow 元管线）执行：
// 场景名去掉 platform. 前缀即动作名，载荷走 {action, payload} 信封。
const WRITE_SCENARIOS: Record<string, string> = {
  "tenants.create": "platform.tenants.create",
  "tenants.update": "platform.tenants.update",
  "tenants.status": "platform.tenants.status",
  "tenants.members.add": "platform.tenants.members.add",
  "tenants.members.set_role": "platform.tenants.members.set_role",
  "tenants.members.remove": "platform.tenants.members.remove",
  "projects.create": "platform.projects.create",
  "projects.update": "platform.projects.update",
  "projects.status": "platform.projects.status",
  "projects.members.add": "platform.projects.members.add",
  "projects.members.set_role": "platform.projects.members.set_role",
  "projects.members.remove": "platform.projects.members.remove",
  "roles.create": "platform.roles.create",
  "roles.update": "platform.roles.update",
  "roles.delete": "platform.roles.delete",
  "users.set_role": "platform.users.set_role",
  "users.set_active": "platform.users.set_active",
  "users.reset_password": "platform.users.reset_password",
};

async function mutate(action: string, payload: Record<string, unknown>) {
  const scenario = WRITE_SCENARIOS[action];
  if (!scenario) throw new Error(`未知的平台治理操作：${action}`);
  return dispatch(scenario, { action, payload });
}

async function run<T>(fn: () => Promise<T>): Promise<string | null> {
  try {
    await fn();
    return null;
  } catch (err) {
    return err instanceof Error ? err.message : String(err);
  }
}

interface RoleOption {
  role_id: string;
  scope: string;
  code: string;
  name: string;
  builtin: boolean;
  tenant_id?: string;
  permissions: string[];
}

function useRoles(scopeFilter?: string) {
  return useQuery({
    queryKey: ["platform", "roles", scopeFilter || "all"],
    queryFn: async () => {
      const data = await dispatch<{ roles: RoleOption[] }>(
        "platform.roles.list",
        scopeFilter ? { scope: scopeFilter } : {},
      );
      return data.roles;
    },
  });
}

function RoleSelect({
  roles,
  value,
  onChange,
  ariaLabel,
}: {
  roles: RoleOption[];
  value: string;
  onChange: (roleId: string) => void;
  ariaLabel: string;
}) {
  return (
    <select
      aria-label={ariaLabel}
      className="h-8 rounded-md border border-border bg-background px-2 text-xs"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {roles.map((r) => (
        <option key={r.role_id} value={r.role_id}>
          {r.name}
        </option>
      ))}
    </select>
  );
}

// ===========================================================================
// 用户管理（平台级）
// ===========================================================================
interface PlatformUser {
  uid: string;
  email: string;
  nickname: string;
  role: string;
  account_type: string;
  is_active: boolean;
}

export function UsersPage() {
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [resetUid, setResetUid] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const invalidate = useInvalidate();
  const list = useQuery({
    queryKey: ["platform", "users", q],
    queryFn: () => dispatch<{ users: PlatformUser[]; total: number }>("platform.users.list", { q, limit: 200 }),
  });

  const setRole = async (uid: string, role: string) => {
    const err = await run(() => mutate("users.set_role", { user_id: uid, role }));
    setError(err);
    if (!err) invalidate("platform", "users");
  };
  const setActive = async (uid: string, is_active: boolean) => {
    const err = await run(() => mutate("users.set_active", { user_id: uid, is_active }));
    setError(err);
    if (!err) invalidate("platform", "users");
  };
  const resetPassword = async (uid: string) => {
    const err = await run(() =>
      mutate("users.reset_password", { user_id: uid, new_password: newPassword }),
    );
    setError(err);
    if (!err) {
      setResetUid("");
      setNewPassword("");
      invalidate("platform", "users");
    }
  };

  return (
    <div>
      <PageHeader title="用户管理" description="平台账号、角色与账号状态（全平台唯一入口）" />
      <Card className="mb-4">
        <CardContent className="flex items-center gap-2 px-4 py-3">
          <Input
            placeholder="搜索邮箱 / 昵称 / uid"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="h-8 max-w-xs text-xs"
          />
          {error && <span className="text-xs text-destructive">{error}</span>}
        </CardContent>
      </Card>
      <Card>
        {list.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !list.data?.users?.length ? (
          <div className="p-5"><EmptyState title="没有匹配的用户" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className={th}>用户</th>
                <th className={th}>平台角色</th>
                <th className={th}>状态</th>
                <th className={th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {list.data.users.map((u) => (
                <tr key={u.uid} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className={td}>
                    <div className="font-medium">{u.nickname || u.email}</div>
                    <div className="text-xs text-muted-foreground">{u.email} · {u.uid}</div>
                  </td>
                  <td className={td}>
                    <select
                      aria-label={`设置 ${u.email} 的平台角色`}
                      className="h-8 rounded-md border border-border bg-background px-2 text-xs"
                      value={u.role}
                      onChange={(e) => setRole(u.uid, e.target.value)}
                    >
                      <option value="ADMIN">平台管理员</option>
                      <option value="MAKER">创客</option>
                      <option value="GUEST">访客</option>
                    </select>
                  </td>
                  <td className={td}>
                    {u.is_active ? <Badge tone="success">启用</Badge> : <Badge tone="destructive">停用</Badge>}
                  </td>
                  <td className={td}>
                    <div className="flex gap-2">
                      <Button variant="secondary" className="h-7 text-xs"
                        onClick={() => setActive(u.uid, !u.is_active)}>
                        {u.is_active ? "停用" : "启用"}
                      </Button>
                      <Button variant="secondary" className="h-7 text-xs"
                        onClick={() => setResetUid(resetUid === u.uid ? "" : u.uid)}>
                        重置密码
                      </Button>
                    </div>
                    {resetUid === u.uid && (
                      <div className="mt-2 flex items-center gap-2">
                        <Input
                          type="password"
                          placeholder="新密码（至少 8 位）"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          className="h-8 max-w-[180px] text-xs"
                        />
                        <Button className="h-7 text-xs" onClick={() => resetPassword(u.uid)}>确认</Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

// ===========================================================================
// 租户管理
// ===========================================================================
interface TenantRow {
  tenant_id: string;
  code: string;
  name: string;
  status: string;
  description: string;
}

interface TenantMember {
  binding_id: string;
  user_id: string;
  email: string;
  nickname: string;
  role_id: string;
  role_name: string;
}

export function TenantsPage() {
  const { hasPermission } = useScope();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ code: "", name: "", description: "" });
  const [openMembers, setOpenMembers] = useState("");
  const invalidate = useInvalidate();
  const canManage = hasPermission("platform:tenant_manage");

  const tenants = useQuery({
    queryKey: ["platform", "tenants"],
    queryFn: () => dispatch<{ tenants: TenantRow[]; total: number }>("platform.tenants.list", {}),
  });
  const tenantRoles = useRoles("TENANT");

  const create = async () => {
    const err = await run(() => mutate("tenants.create", form));
    setError(err);
    if (!err) {
      setForm({ code: "", name: "", description: "" });
      invalidate("platform", "tenants");
    }
  };
  const setStatus = async (tenant_id: string, status: string) => {
    const err = await run(() => mutate("tenants.status", { tenant_id, status }));
    setError(err);
    if (!err) invalidate("platform", "tenants");
  };

  return (
    <div>
      <PageHeader title="租户管理" description="组织实体与其成员；项目挂在租户下" />
      {error && <div className="mb-3 text-xs text-destructive">{error}</div>}
      <PermissionGate permission="platform:tenant_manage">
        <Card className="mb-4">
          <CardHeader><CardTitle>创建租户</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-2">
            <div>
              <div className="mb-1 text-xs text-muted-foreground">编码（小写字母/数字/连字符）</div>
              <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="h-8 w-44 text-xs" />
            </div>
            <div>
              <div className="mb-1 text-xs text-muted-foreground">名称</div>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="h-8 w-44 text-xs" />
            </div>
            <div>
              <div className="mb-1 text-xs text-muted-foreground">描述</div>
              <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="h-8 w-60 text-xs" />
            </div>
            <Button className="h-8 text-xs" onClick={create}>创建（创建人自动成为租户管理员）</Button>
          </CardContent>
        </Card>
      </PermissionGate>
      <Card>
        {tenants.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !tenants.data?.tenants?.length ? (
          <div className="p-5"><EmptyState title="暂无租户" hint={canManage ? "先创建一个租户开始组织协作。" : "请联系平台管理员加入租户。"} /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className={th}>租户</th>
                <th className={th}>状态</th>
                <th className={th}>成员</th>
                {canManage && <th className={th}>操作</th>}
              </tr>
            </thead>
            <tbody>
              {tenants.data.tenants.map((t) => (
                <tr key={t.tenant_id} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className={td}>
                    <div className="font-medium">{t.name}</div>
                    <div className="text-xs text-muted-foreground">{t.code}{t.description ? ` · ${t.description}` : ""}</div>
                  </td>
                  <td className={td}>
                    {t.status === "ACTIVE" ? <Badge tone="success">启用</Badge> : <Badge tone="warning">停用</Badge>}
                  </td>
                  <td className={td}>
                    <Button variant="secondary" className="h-7 text-xs"
                      onClick={() => setOpenMembers(openMembers === t.tenant_id ? "" : t.tenant_id)}>
                      成员
                    </Button>
                  </td>
                  {canManage && (
                    <td className={td}>
                      <Button variant="secondary" className="h-7 text-xs"
                        onClick={() => setStatus(t.tenant_id, t.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE")}>
                        {t.status === "ACTIVE" ? "停用" : "启用"}
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {openMembers && (
        <TenantMembersPanel
          tenantId={openMembers}
          roles={tenantRoles.data || []}
          canManage={canManage || hasPermission("tenant:member_manage")}
        />
      )}
    </div>
  );
}

function TenantMembersPanel({
  tenantId,
  roles,
  canManage,
}: {
  tenantId: string;
  roles: RoleOption[];
  canManage: boolean;
}) {
  const [error, setError] = useState<string | null>(null);
  const [account, setAccount] = useState("");
  const [roleId, setRoleId] = useState("");
  const invalidate = useInvalidate();
  const members = useQuery({
    queryKey: ["platform", "tenant-members", tenantId],
    queryFn: () => dispatch<{ members: TenantMember[] }>("platform.tenants.members.list", { tenant_id: tenantId }),
  });

  const add = async () => {
    const err = await run(() =>
      mutate("tenants.members.add", { tenant_id: tenantId, email: account, role_id: roleId || undefined }),
    );
    setError(err);
    if (!err) {
      setAccount("");
      invalidate("platform", "tenant-members");
    }
  };
  const setRole = async (userId: string, nextRole: string) => {
    const err = await run(() =>
      mutate("tenants.members.set_role", { tenant_id: tenantId, user_id: userId, role_id: nextRole }),
    );
    setError(err);
    if (!err) invalidate("platform", "tenant-members");
  };
  const remove = async (userId: string) => {
    const err = await run(() =>
      mutate("tenants.members.remove", { tenant_id: tenantId, user_id: userId }),
    );
    setError(err);
    if (!err) invalidate("platform", "tenant-members");
  };

  return (
    <Card className="mt-4">
      <CardHeader><CardTitle>租户成员</CardTitle></CardHeader>
      <CardContent>
        {error && <div className="mb-2 text-xs text-destructive">{error}</div>}
        {canManage && (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Input placeholder="邮箱或 uid" value={account} onChange={(e) => setAccount(e.target.value)} className="h-8 w-56 text-xs" />
            <RoleSelect roles={roles} value={roleId} onChange={setRoleId} ariaLabel="选择租户角色" />
            <Button className="h-8 text-xs" onClick={add}>添加成员</Button>
          </div>
        )}
        {members.isPending ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : !members.data?.members?.length ? (
          <EmptyState title="暂无成员" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className={th}>成员</th>
                <th className={th}>角色</th>
                {canManage && <th className={th}>操作</th>}
              </tr>
            </thead>
            <tbody>
              {members.data.members.map((m) => (
                <tr key={m.binding_id} className="border-b border-border/60 last:border-0">
                  <td className={td}>
                    <div className="font-medium">{m.nickname || m.email}</div>
                    <div className="text-xs text-muted-foreground">{m.email}</div>
                  </td>
                  <td className={td}>
                    {canManage ? (
                      <RoleSelect roles={roles} value={m.role_id} onChange={(r) => setRole(m.user_id, r)} ariaLabel={`调整 ${m.email} 的角色`} />
                    ) : (
                      <Badge>{m.role_name}</Badge>
                    )}
                  </td>
                  {canManage && (
                    <td className={td}>
                      <Button variant="destructive" className="h-7 text-xs" onClick={() => remove(m.user_id)}>移出</Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

// ===========================================================================
// 项目管理
// ===========================================================================
interface ProjectRow {
  project_id: string;
  tenant_id: string;
  key: string;
  name: string;
  status: string;
  description: string;
  my_role: string;
}

interface ProjectMember extends TenantMember {}

export function ProjectsPage() {
  const { myScope, hasPermission } = useScope();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ tenant_id: "", key: "", name: "", description: "" });
  const [openMembers, setOpenMembers] = useState("");
  const invalidate = useInvalidate();
  const canCreate = hasPermission("tenant:project_create");
  const canManageMembers = hasPermission("project:member_manage") || hasPermission("tenant:member_manage");

  const projects = useQuery({
    queryKey: ["platform", "projects"],
    queryFn: () => dispatch<{ projects: ProjectRow[] }>("platform.projects.list", {}),
  });
  const projectRoles = useRoles("PROJECT");

  const create = async () => {
    const err = await run(() => mutate("projects.create", form));
    setError(err);
    if (!err) {
      setForm({ tenant_id: "", key: "", name: "", description: "" });
      invalidate("platform", "projects");
    }
  };
  const setStatus = async (project_id: string, status: string) => {
    const err = await run(() => mutate("projects.status", { project_id, status }));
    setError(err);
    if (!err) invalidate("platform", "projects");
  };

  return (
    <div>
      <PageHeader title="项目管理" description="编排资产与支撑平台操作的作用域单位；项目间相互隔离" />
      {error && <div className="mb-3 text-xs text-destructive">{error}</div>}
      {canCreate && (
        <Card className="mb-4">
          <CardHeader><CardTitle>创建项目</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-2">
            <div>
              <div className="mb-1 text-xs text-muted-foreground">所属租户</div>
              <select
                aria-label="选择所属租户"
                className="h-8 rounded-md border border-border bg-background px-2 text-xs"
                value={form.tenant_id}
                onChange={(e) => setForm({ ...form, tenant_id: e.target.value })}
              >
                <option value="">选择租户</option>
                {(myScope?.tenants || []).map((t) => (
                  <option key={t.tenant_id} value={t.tenant_id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <div className="mb-1 text-xs text-muted-foreground">项目标识（小写字母/数字/连字符）</div>
              <Input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} className="h-8 w-40 text-xs" />
            </div>
            <div>
              <div className="mb-1 text-xs text-muted-foreground">名称</div>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="h-8 w-40 text-xs" />
            </div>
            <div>
              <div className="mb-1 text-xs text-muted-foreground">描述</div>
              <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="h-8 w-56 text-xs" />
            </div>
            <Button className="h-8 text-xs" onClick={create}>创建（创建人自动成为项目所有者）</Button>
          </CardContent>
        </Card>
      )}
      <Card>
        {projects.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !projects.data?.projects?.length ? (
          <div className="p-5"><EmptyState title="暂无项目" hint="加入租户后由租户管理员或项目所有者创建项目。" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className={th}>项目</th>
                <th className={th}>我的角色</th>
                <th className={th}>状态</th>
                <th className={th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {projects.data.projects.map((p) => (
                <tr key={p.project_id} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className={td}>
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.key}{p.description ? ` · ${p.description}` : ""}</div>
                  </td>
                  <td className={td}>{p.my_role ? <Badge tone="primary">{p.my_role}</Badge> : <Badge>租户在册</Badge>}</td>
                  <td className={td}>
                    {p.status === "ACTIVE" ? <Badge tone="success">进行中</Badge> : <Badge tone="warning">已归档</Badge>}
                  </td>
                  <td className={td}>
                    <div className="flex gap-2">
                      <Button variant="secondary" className="h-7 text-xs"
                        onClick={() => setOpenMembers(openMembers === p.project_id ? "" : p.project_id)}>
                        成员
                      </Button>
                      {hasPermission("project:manage") && (
                        <Button variant="secondary" className="h-7 text-xs"
                          onClick={() => setStatus(p.project_id, p.status === "ACTIVE" ? "ARCHIVED" : "ACTIVE")}>
                          {p.status === "ACTIVE" ? "归档" : "恢复"}
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {openMembers && (
        <ProjectMembersPanel
          projectId={openMembers}
          roles={projectRoles.data || []}
          canManage={canManageMembers}
        />
      )}
    </div>
  );
}

function ProjectMembersPanel({
  projectId,
  roles,
  canManage,
}: {
  projectId: string;
  roles: RoleOption[];
  canManage: boolean;
}) {
  const [error, setError] = useState<string | null>(null);
  const [account, setAccount] = useState("");
  const [roleId, setRoleId] = useState("");
  const invalidate = useInvalidate();
  const members = useQuery({
    queryKey: ["platform", "project-members", projectId],
    queryFn: () => dispatch<{ members: ProjectMember[] }>("platform.projects.members.list", { project_id: projectId }),
  });

  const add = async () => {
    const err = await run(() =>
      mutate("projects.members.add", { project_id: projectId, email: account, role_id: roleId || undefined }),
    );
    setError(err);
    if (!err) {
      setAccount("");
      invalidate("platform", "project-members");
    }
  };
  const setRole = async (userId: string, nextRole: string) => {
    const err = await run(() =>
      mutate("projects.members.set_role", { project_id: projectId, user_id: userId, role_id: nextRole }),
    );
    setError(err);
    if (!err) invalidate("platform", "project-members");
  };
  const remove = async (userId: string) => {
    const err = await run(() =>
      mutate("projects.members.remove", { project_id: projectId, user_id: userId }),
    );
    setError(err);
    if (!err) invalidate("platform", "project-members");
  };

  return (
    <Card className="mt-4">
      <CardHeader><CardTitle>项目成员</CardTitle></CardHeader>
      <CardContent>
        {error && <div className="mb-2 text-xs text-destructive">{error}</div>}
        {canManage && (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Input placeholder="邮箱或 uid（须已在册于所属租户）" value={account} onChange={(e) => setAccount(e.target.value)} className="h-8 w-64 text-xs" />
            <RoleSelect roles={roles} value={roleId} onChange={setRoleId} ariaLabel="选择项目角色" />
            <Button className="h-8 text-xs" onClick={add}>添加成员</Button>
          </div>
        )}
        {members.isPending ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : !members.data?.members?.length ? (
          <EmptyState title="暂无成员" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className={th}>成员</th>
                <th className={th}>角色</th>
                {canManage && <th className={th}>操作</th>}
              </tr>
            </thead>
            <tbody>
              {members.data.members.map((m) => (
                <tr key={m.binding_id} className="border-b border-border/60 last:border-0">
                  <td className={td}>
                    <div className="font-medium">{m.nickname || m.email}</div>
                    <div className="text-xs text-muted-foreground">{m.email}</div>
                  </td>
                  <td className={td}>
                    {canManage ? (
                      <RoleSelect roles={roles} value={m.role_id} onChange={(r) => setRole(m.user_id, r)} ariaLabel={`调整 ${m.email} 的项目角色`} />
                    ) : (
                      <Badge>{m.role_name}</Badge>
                    )}
                  </td>
                  {canManage && (
                    <td className={td}>
                      <Button variant="destructive" className="h-7 text-xs" onClick={() => remove(m.user_id)}>移出</Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

// ===========================================================================
// 角色管理（可配置 RBAC）
// ===========================================================================
interface PermissionItem {
  permission: string;
  builtin_role: string;
}

export function RolesPage() {
  const { myScope, hasPermission } = useScope();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ scope: "PROJECT", code: "", name: "", description: "" });
  const [checked, setChecked] = useState<string[]>([]);
  const [editing, setEditing] = useState("");
  const [editChecked, setEditChecked] = useState<string[]>([]);
  const invalidate = useInvalidate();
  const canManage = hasPermission("platform:role_manage") || hasPermission("tenant:role_manage");

  const roles = useQuery({
    queryKey: ["platform", "roles", "manage"],
    queryFn: () => dispatch<{ roles: RoleOption[] }>("platform.roles.list", {}),
  });
  const permissions = useQuery({
    queryKey: ["platform", "permissions"],
    queryFn: () => dispatch<{ permissions: PermissionItem[] }>("platform.permissions.list", {}),
  });

  const create = async () => {
    const tenantId = myScope?.tenants[0]?.tenant_id || "";
    const err = await run(() =>
      mutate("roles.create", { ...form, tenant_id: tenantId, permissions: checked }),
    );
    setError(err);
    if (!err) {
      setForm({ scope: "PROJECT", code: "", name: "", description: "" });
      setChecked([]);
      invalidate("platform", "roles");
    }
  };
  const savePermissions = async (roleId: string) => {
    const err = await run(() =>
      mutate("roles.update", { role_id: roleId, permissions: editChecked }),
    );
    setError(err);
    if (!err) {
      setEditing("");
      invalidate("platform", "roles");
    }
  };
  const remove = async (roleId: string) => {
    const err = await run(() => mutate("roles.delete", { role_id: roleId }));
    setError(err);
    if (!err) invalidate("platform", "roles");
  };

  return (
    <div>
      <PageHeader title="角色与权限" description="可配置角色：权限点按范围（平台/租户/项目）授予" />
      {error && <div className="mb-3 text-xs text-destructive">{error}</div>}
      {canManage && (
        <Card className="mb-4">
          <CardHeader><CardTitle>创建自定义角色</CardTitle></CardHeader>
          <CardContent>
            <div className="mb-3 flex flex-wrap items-end gap-2">
              <div>
                <div className="mb-1 text-xs text-muted-foreground">生效范围</div>
                <select
                  aria-label="选择角色生效范围"
                  className="h-8 rounded-md border border-border bg-background px-2 text-xs"
                  value={form.scope}
                  onChange={(e) => setForm({ ...form, scope: e.target.value })}
                >
                  <option value="PROJECT">项目</option>
                  <option value="TENANT">租户</option>
                </select>
              </div>
              <div>
                <div className="mb-1 text-xs text-muted-foreground">编码</div>
                <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="h-8 w-44 text-xs" />
              </div>
              <div>
                <div className="mb-1 text-xs text-muted-foreground">名称</div>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="h-8 w-40 text-xs" />
              </div>
              <div>
                <div className="mb-1 text-xs text-muted-foreground">描述</div>
                <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="h-8 w-56 text-xs" />
              </div>
            </div>
            <div className="mb-3 flex flex-wrap gap-2">
              {(permissions.data?.permissions || []).map((p) => (
                <label key={p.permission} className="flex items-center gap-1.5 text-xs">
                  <input
                    type="checkbox"
                    checked={checked.includes(p.permission)}
                    onChange={(e) =>
                      setChecked(e.target.checked ? [...checked, p.permission] : checked.filter((x) => x !== p.permission))
                    }
                  />
                  {p.permission}
                </label>
              ))}
            </div>
            <Button className="h-8 text-xs" onClick={create}>创建角色</Button>
          </CardContent>
        </Card>
      )}
      <Card>
        {roles.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className={th}>角色</th>
                <th className={th}>范围</th>
                <th className={th}>权限点</th>
                {canManage && <th className={th}>操作</th>}
              </tr>
            </thead>
            <tbody>
              {(roles.data?.roles || []).map((r) => (
                <tr key={r.role_id} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className={td}>
                    <div className="font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground">{r.code}</div>
                  </td>
                  <td className={td}>
                    <Badge tone={r.scope === "PLATFORM" ? "primary" : r.scope === "TENANT" ? "warning" : "success"}>
                      {r.scope === "PLATFORM" ? "平台" : r.scope === "TENANT" ? "租户" : "项目"}
                    </Badge>
                  </td>
                  <td className={td}>
                    {editing === r.role_id ? (
                      <div className="max-w-lg">
                        <div className="mb-2 flex flex-wrap gap-2">
                          {(permissions.data?.permissions || []).map((p) => (
                            <label key={p.permission} className="flex items-center gap-1.5 text-xs">
                              <input
                                type="checkbox"
                                checked={editChecked.includes(p.permission)}
                                onChange={(e) =>
                                  setEditChecked(
                                    e.target.checked
                                      ? [...editChecked, p.permission]
                                      : editChecked.filter((x) => x !== p.permission),
                                  )
                                }
                              />
                              {p.permission}
                            </label>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <Button className="h-7 text-xs" onClick={() => savePermissions(r.role_id)}>保存</Button>
                          <Button variant="secondary" className="h-7 text-xs" onClick={() => setEditing("")}>取消</Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {r.permissions.includes("*") ? (
                          <Badge tone="primary">全部权限</Badge>
                        ) : r.permissions.length ? (
                          r.permissions.map((p) => <Badge key={p}>{p}</Badge>)
                        ) : (
                          <span className="text-xs text-muted-foreground">无</span>
                        )}
                      </div>
                    )}
                  </td>
                  {canManage && (
                    <td className={td}>
                      {!r.builtin && (
                        <div className="flex gap-2">
                          <Button variant="secondary" className="h-7 text-xs"
                            onClick={() => {
                              setEditing(editing === r.role_id ? "" : r.role_id);
                              setEditChecked(r.permissions);
                            }}>
                            调整权限
                          </Button>
                          <Button variant="destructive" className="h-7 text-xs" onClick={() => remove(r.role_id)}>删除</Button>
                        </div>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
