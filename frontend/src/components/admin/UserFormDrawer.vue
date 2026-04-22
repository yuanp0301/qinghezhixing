<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import { createUser, updateUser } from "@/api/admin";
import { toastSuccess } from "@/utils/feedback";
import type { Role, UserAdmin } from "@/types/models";

const props = defineProps<{ visible: boolean; user: UserAdmin | null }>();
const emit = defineEmits<{
  (e: "update:visible", v: boolean): void;
  (e: "saved"): void;
}>();

const formRef = ref<FormInstance>();
const saving = ref(false);
const form = reactive<{
  username: string;
  password: string;
  role: Role;
  note: string;
}>({
  username: "",
  password: "",
  role: "viewer",
  note: "",
});

const rules: FormRules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    {
      pattern: /^[a-zA-Z0-9_]{2,32}$/,
      message: "2–32 字，英数下划线",
      trigger: "blur",
    },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    {
      pattern: /^(?=.*[A-Za-z])(?=.*\d).{8,64}$/,
      message: "8–64 字，至少含字母与数字",
      trigger: "blur",
    },
  ],
  role: [{ required: true, message: "请选择角色" }],
};

watch(
  () => props.visible,
  (v) => {
    if (!v) return;
    if (props.user) {
      form.username = props.user.username;
      form.password = "";
      form.role = props.user.role;
      form.note = props.user.note ?? "";
    } else {
      form.username = "";
      form.password = "";
      form.role = "viewer";
      form.note = "";
    }
  },
);

async function onSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate();
  saving.value = true;
  try {
    if (props.user) {
      await updateUser(props.user.id, {
        role: form.role,
        note: form.note || null,
      });
      toastSuccess("已保存");
    } else {
      await createUser({
        username: form.username,
        password: form.password,
        role: form.role,
        note: form.note || undefined,
      });
      toastSuccess("用户已创建");
    }
    emit("saved");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <el-drawer
    :model-value="visible"
    :title="user ? '编辑用户' : '新建用户'"
    size="440px"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
    >
      <el-form-item
        label="用户名"
        prop="username"
      >
        <el-input
          v-model="form.username"
          :disabled="!!user"
          placeholder="2–32 字，英数下划线"
        />
      </el-form-item>
      <el-form-item
        v-if="!user"
        label="初始密码"
        prop="password"
      >
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="8–64 字，至少含字母与数字"
        />
      </el-form-item>
      <el-form-item
        label="角色"
        prop="role"
      >
        <el-radio-group v-model="form.role">
          <el-radio value="viewer">
            viewer
          </el-radio>
          <el-radio value="creator">
            creator
          </el-radio>
          <el-radio value="admin">
            admin
          </el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item
        label="备注"
        prop="note"
      >
        <el-input
          v-model="form.note"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">
        取消
      </el-button>
      <el-button
        type="primary"
        :loading="saving"
        @click="onSubmit"
      >
        保存
      </el-button>
    </template>
  </el-drawer>
</template>
