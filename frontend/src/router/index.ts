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
