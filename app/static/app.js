const { createApp, ref, onMounted, computed } = Vue;

// axios 拦截器：自动带 token，401 跳登录
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

axios.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

createApp({
  setup() {
    const user = ref(JSON.parse(localStorage.getItem("user") || "null"));
    const reports = ref([]);
    const versions = ref([]);
    const detail = ref(null);
    const loading = ref(false);
    const submitting = ref(false);
    const form = ref({ title: "", content: "", format: "xlsx" });
    const toast = ref("");

    const isAdmin = computed(() =>
      user.value?.roles?.includes("admin")
    );

    const statusText = (s) => ({
      draft: "草稿",
      pending_review: "待审核",
      approved: "已审核",
      archived: "已归档",
    }[s] || s);

    const showToast = (msg) => {
      toast.value = msg;
      setTimeout(() => (toast.value = ""), 2500);
    };

    const loadReports = async () => {
      loading.value = true;
      try {
        const res = await axios.get("/api/report");
        reports.value = res.data.items || [];
      } catch (e) {
        showToast("加载失败：" + e.message);
      } finally {
        loading.value = false;
      }
    };

    const submitReport = async () => {
      if (!form.value.title) return showToast("标题不能为空");
      submitting.value = true;
      try {
        await axios.post("/api/report", form.value);
        showToast("提交成功，报告生成中...");
        form.value = { title: "", content: "", format: "xlsx" };
        setTimeout(loadReports, 2000);
      } catch (e) {
        showToast("提交失败：" + (e.response?.data?.error || e.message));
      } finally {
        submitting.value = false;
      }
    };

    const openDetail = async (r) => {
      const res = await axios.get(`/api/report/${r.id}`);
      detail.value = res.data;
      const vres = await axios.get(`/api/report/${r.id}/versions`);
      versions.value = vres.data.items || [];
    };

    const approve = async (r) => {
      if (!confirm(`确定审批报告 ${r.report_no}？`)) return;
      try {
        await axios.post(`/api/report/${r.id}/approve`);
        showToast("审批成功");
        loadReports();
      } catch (e) {
        showToast("审批失败：" + (e.response?.data?.error || e.message));
      }
    };

    const archive = async (r) => {
      if (!confirm(`确定归档报告 ${r.report_no}？`)) return;
      try {
        await axios.post(`/api/report/${r.id}/archive`);
        showToast("归档成功");
        loadReports();
      } catch (e) {
        showToast("归档失败：" + (e.response?.data?.error || e.message));
      }
    };

    const regenerate = async (r) => {
      const fmt = prompt("重新生成格式：xlsx 或 pdf", "pdf");
      if (!fmt) return;
      try {
        await axios.post(`/api/report/${r.id}/regenerate`, { format: fmt });
        showToast("正在重新生成，版本 +0.1");
        setTimeout(loadReports, 2500);
      } catch (e) {
        showToast("重新生成失败：" + (e.response?.data?.error || e.message));
      }
    };

    const download = async (reportId, version) => {
      try {
        const res = await axios.get(
          `/api/report/${reportId}/download/${version}`,
          { responseType: "blob" }
        );
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement("a");
        a.href = url;
        const ext = res.headers["content-type"].includes("pdf") ? "pdf" : "xlsx";
        a.download = `report-${reportId}-${version}.${ext}`;
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (e) {
        showToast("下载失败：" + e.message);
      }
    };

    const logout = () => {
      localStorage.clear();
      window.location.href = "/login";
    };

    onMounted(() => {
      if (!localStorage.getItem("access_token")) {
        window.location.href = "/login";
        return;
      }
      loadReports();
    });

    const selectedIds = ref([]);

const allSelected = computed(() =>
  reports.value.length > 0 && selectedIds.value.length === reports.value.length
);

const toggleAll = (e) => {
  if (e.target.checked) {
    selectedIds.value = reports.value.map((r) => r.id);
  } else {
    selectedIds.value = [];
  }
};

const batchExport = async () => {
  if (selectedIds.value.length === 0) {
    return showToast("请先勾选报告");
  }
  try {
    const res = await axios.post(
      "/api/report/batch-export",
      { report_ids: selectedIds.value },
      { responseType: "blob" }
    );

    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `reports_${Date.now()}.zip`;
    a.click();
    window.URL.revokeObjectURL(url);

    showToast("导出成功");
  } catch (e) {
    showToast("导出失败：" + e.message);
  }
};

    return {
      user, isAdmin, reports, versions, detail, loading, submitting,
      form, toast,
      statusText, loadReports, submitReport, openDetail,
      approve, archive, regenerate, download, logout,
      selectedIds, allSelected, toggleAll, batchExport,
    };
  },
}).mount("#app");