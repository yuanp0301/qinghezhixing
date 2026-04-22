import { createRouter, createWebHistory } from "vue-router";
import { installGuards } from "./guards";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/contents",
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { layout: "blank" },
    },
    {
      path: "/contents",
      component: () => import("@/layouts/AppLayout.vue"),
      children: [
        {
          path: "",
          name: "contents",
          component: () => import("@/views/ContentsView.vue"),
        },
        {
          path: "mine",
          name: "my-contents",
          component: () => import("@/views/MyContentsView.vue"),
          meta: { requiresRole: "creator" },
        },
        {
          path: "new",
          name: "content-new",
          component: () => import("@/views/ContentUploadView.vue"),
          meta: { requiresRole: "creator" },
        },
        {
          path: ":id(\\d+)",
          name: "content-detail",
          component: () => import("@/views/ContentDetailView.vue"),
        },
      ],
    },
    {
      path: "/admin",
      component: () => import("@/layouts/AppLayout.vue"),
      meta: { requiresRole: "admin" },
      children: [
        {
          path: "contents",
          name: "admin-contents",
          component: () => import("@/views/admin/AdminContentsView.vue"),
          meta: { requiresRole: "admin", title: "全部内容" },
        },
        {
          path: "users",
          name: "admin-users",
          component: () => import("@/views/admin/AdminUsersView.vue"),
          meta: { requiresRole: "admin", title: "用户管理" },
        },
        {
          path: "tags",
          name: "admin-tags",
          component: () => import("@/views/admin/AdminTagsView.vue"),
          meta: { requiresRole: "admin", title: "标签管理" },
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/contents",
    },
  ],
});

installGuards(router);
