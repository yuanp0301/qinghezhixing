module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "@typescript-eslint/parser",
    sourceType: "module",
    ecmaVersion: "latest",
  },
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-recommended",
  ],
  rules: {
    "vue/multi-word-component-names": "off",
    "no-unused-vars": ["error", { args: "none" }],
  },
};
