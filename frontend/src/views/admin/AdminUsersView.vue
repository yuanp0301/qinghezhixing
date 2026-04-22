<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessageBox } from "element-plus";
import PageHeader from "@/components/PageHeader.vue";
import UserFormDrawer from "@/components/admin/UserFormDrawer.vue";
import ResetPasswordDialog from "@/components/admin/ResetPasswordDialog.vue";
import { listUsers, updateUser } from "@/api/admin";
import { toastSuccess } from "@/utils/feedback";
import { formatAbs } from "@/utils/time";
import type { Role, UserAdmin } from "@/types/models";

const rows = ref<UserAdmin[]>([]);
const total = ref(0);
const loading = ref(false);
const page = ref(1);
const pageSize = 20;
const q = ref("");
const role = ref<Role | undefined>();
const status = ref<"active" | "disabled" | undefined>();

const formVisible = ref(false);
const editing = ref<UserAdmin | null>(null);
const resetVisible = ref(false);
const resetting = ref<UserAdmin | null>(null);

async function reload() {
  loading.value = true;
  try {
    const data = await listUsers({
      q: q.value || undefined,
      role: role.value,
      status: status.value,
      page: page.value,
      size: pageSize,
    });
    rows.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  formVisible.value = true;
}

function openEdit(row: UserAdmin) {
  editing.value = row;
  formVisible.value = true;
}

function openReset(row: UserAdmin) {
  resetting.value = row;
  resetVisible.value = true;
}

async function toggleActive(row: UserAdmin) {
  const isActive = row.status === "active";
  const nextStatus: "active" | "disabled" = isActive ? "disabled" : "active";
  if (nextStatus === "disabled") {
    try {
      await ElMessageBox.confirm(
        "禁用后该用户无法登录，已有会话将在下次请求时失效。",
        "禁用用户",
        {
          type: "warning",
          confirmButtonText: "确认禁用",
          cancelButtonText: "取消",
        },
      );
    } catch {
      return;
    }
  }
  await updateUser(row.id, { status: nextStatus });
  toastSuccess(nextStatus === "active" ? "已启用" : "已禁用");
  reload();
}

function onSaved() {
  formVisible.value = false;
  reload();
}

function onPageChange(p: number) {
  page.value = p;
  reload();
}

onMounted(reload);
</script>

<template>
  <div class="page-wrap">
    <PageHeader title="用户管理">
      <template #actions>
        <el-button
          type="primary"
          @click="openCreate"
        >
          新建用户
        </el-button>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <el-input
        v-model="q"
        placeholder="搜索用户名"
        clearable
        style="width: 240px"
        @change="reload"
      />
      <el-select
        v-model="role"
        placeholder="角色"
        clearable
        style="width: 140px"
        @change="reload"
      >
        <el-option
          label="admin"
          value="admin"
        />
        <el-option
          label="creator"
          value="creator"
        />
        <el-option
          label="viewer"
          value="viewer"
        />
      </el-select>
      <el-select
        v-model="status"
        placeholder="状态"
        clearable
        style="width: 140px"
        @change="reload"
      >
        <el-option
          label="启用"
          value="active"
        />
        <el-option
          label="禁用"
          value="disabled"
        />
      </el-select>
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      stripe
    >
      <el-table-column
        prop="username"
        label="用户名"
        min-width="160"
      />
      <el-table-column
        prop="role"
        label="角色"
        width="120"
      />
      <el-table-column
        label="状态"
        width="100"
      >
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        label="创建时间"
        width="170"
      >
        <template #default="{ row }">
          {{ formatAbs(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column
        label="最近登录"
        width="170"
      >
        <template #default="{ row }">
          {{ row.last_login_at ? formatAbs(row.last_login_at) : '—' }}
        </template>
      </el-table-column>
      <el-table-column
        label="操作"
        width="260"
        fixed="right"
      >
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click="openEdit(row)"
          >
            编辑
          </el-button>
          <el-button
            link
            type="primary"
            @click="openReset(row)"
          >
            重置密码
          </el-button>
          <el-button
            link
            :type="row.status === 'active' ? 'danger' : 'primary'"
            @click="toggleActive(row)"
          >
            {{ row.status === 'active' ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      class="pager"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next, total"
      @current-change="onPageChange"
    />

    <UserFormDrawer
      v-model:visible="formVisible"
      :user="editing"
      @saved="onSaved"
    />
    <ResetPasswordDialog
      v-model:visible="resetVisible"
      :user="resetting"
    />
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px 32px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  margin: 16px 0;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
</style>
