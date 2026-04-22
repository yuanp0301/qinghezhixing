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
      path: "/:pathMatch(.*)*",
      redirect: "/contents",
    },
  ],
});

installGuards(router);
