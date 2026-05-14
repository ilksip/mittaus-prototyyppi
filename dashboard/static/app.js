const API_BASE = "/api";

const deviceColumns = [
  { key: "serial_number", label: "Serial", type: "readonly" },
  { key: "device_id", label: "Device ID", type: "readonly", truncate: 8 },
  { key: "mac_address", label: "MAC", type: "readonly" },
  { key: "device_name", label: "Name", type: "text" },
  { key: "bin_height", label: "Bin Height (cm)", type: "number", min: 1 },
  { key: "height_buffer", label: "Buffer (cm)", type: "number", min: 0 },
  { key: "alerts_enabled", label: "Alerts", type: "checkbox" },
];

const contactColumns = [
  { key: "contact_id", label: "ID", type: "readonly" },
  { key: "name", label: "Name", type: "text" },
  { key: "email", label: "Email", type: "email" },
];

function dashboard() {
  return {
    activeTab: "devices",
    loading: false,
    error: "",
    message: "",
    devices: [],
    contacts: [],
    deviceColumns,
    contactColumns,
    newContact: { name: "", email: "" },
    selectedAssignmentDeviceId: "",
    selectedRecipientIds: [],
    selectedTelemetryDeviceId: "",
    telemetryLimit: 100,
    telemetryRows: [],
    chart: null,

    get selectedTelemetryDevice() {
      return this.devices.find((device) => device.device_id === this.selectedTelemetryDeviceId);
    },

    get latestFillLabel() {
      const points = this.fillPercentagePoints();
      const latest = points.at(-1);
      return latest && Number.isFinite(latest.y) ? `${latest.y.toFixed(1)}%` : "-";
    },

    get telemetryRangeLabel() {
      const rows = this.telemetryRows;
      if (!rows.length) return "-";

      const first = this.formatDate(rows[0].created_at);
      const last = this.formatDate(rows.at(-1).created_at);
      return `${first} to ${last}`;
    },

    async init() {
      await this.refreshAll();
    },

    async refreshAll() {
      await this.run(async () => {
        const [devices, contacts] = await Promise.all([
          this.request("/devices"),
          this.request("/contacts"),
        ]);
        this.devices = devices;
        this.contacts = contacts;

        if (!this.selectedAssignmentDeviceId && devices.length) {
          this.selectedAssignmentDeviceId = devices[0].device_id;
          await this.loadRecipients(false);
        }
        if (!this.selectedTelemetryDeviceId && devices.length) {
          this.selectedTelemetryDeviceId = devices[0].device_id;
        }
      });
    },

    async request(path, options = {}) {
      const response = await fetch(`${API_BASE}${path}`, {
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
        ...options,
      });

      const contentType = response.headers.get("content-type") || "";
      const body = contentType.includes("application/json") ? await response.json() : null;

      if (!response.ok) {
        throw new Error(body?.error || body?.message || `Request failed with ${response.status}`);
      }

      return body;
    },

    async run(task, successMessage = "") {
      this.loading = true;
      this.error = "";
      this.message = "";

      try {
        const result = await task();
        if (successMessage) this.message = successMessage;
        return result;
      } catch (err) {
        this.error = err.message || "Unexpected dashboard error.";
        throw err;
      } finally {
        this.loading = false;
      }
    },

    formatValue(value, column) {
      if (value === null || value === undefined) return "";
      const text = String(value);
      return column.truncate && text.length > column.truncate
        ? `${text.slice(0, column.truncate)}...`
        : text;
    },

    deviceLabel(device) {
      return `${device.device_name || "Unnamed device"} (${String(device.device_id).slice(0, 8)})`;
    },

    async saveDevice(device) {
      await this.run(async () => {
        await this.request(`/devices/${device.device_id}`, {
          method: "PUT",
          body: JSON.stringify({
            device_name: device.device_name,
            bin_height: Number(device.bin_height),
            height_buffer: Number(device.height_buffer),
            alerts_enabled: Boolean(device.alerts_enabled),
          }),
        });
      }, "Device saved.");
    },

    async createContact() {
      await this.run(async () => {
        await this.request("/contacts", {
          method: "POST",
          body: JSON.stringify(this.newContact),
        });
        this.newContact = { name: "", email: "" };
        this.contacts = await this.request("/contacts");
      }, "Contact added.");
    },

    async saveContact(contact) {
      await this.run(async () => {
        await this.request(`/contacts/${contact.contact_id}`, {
          method: "PUT",
          body: JSON.stringify({
            name: contact.name,
            email: contact.email,
          }),
        });
      }, "Contact saved.");
    },

    async deleteContact(contact) {
      if (!confirm(`Delete ${contact.name}?`)) return;

      await this.run(async () => {
        await this.request(`/contacts/${contact.contact_id}`, { method: "DELETE" });
        this.contacts = this.contacts.filter((item) => item.contact_id !== contact.contact_id);
        this.selectedRecipientIds = this.selectedRecipientIds.filter((id) => id !== contact.contact_id);
      }, "Contact deleted.");
    },

    async loadRecipients(showErrors = true) {
      if (!this.selectedAssignmentDeviceId) {
        this.selectedRecipientIds = [];
        return;
      }

      const load = async () => {
        this.selectedRecipientIds = await this.request(`/devices/${this.selectedAssignmentDeviceId}/recipients`);
      };

      if (showErrors) {
        await this.run(load);
      } else {
        await load();
      }
    },

    async saveRecipients() {
      await this.run(async () => {
        await this.request(`/devices/${this.selectedAssignmentDeviceId}/recipients`, {
          method: "POST",
          body: JSON.stringify({ contact_ids: this.selectedRecipientIds.map(Number) }),
        });
      }, "Assignments saved.");
    },

    async fetchTelemetry() {
      if (!this.selectedTelemetryDeviceId) return;

      await this.run(async () => {
        const rows = await this.request(
          `/devices/${this.selectedTelemetryDeviceId}/telemetry?limit=${this.telemetryLimit}`,
        );
        this.telemetryRows = rows
          .slice()
          .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        this.renderChart();
      });
    },

    fillPercentagePoints() {
      const device = this.selectedTelemetryDevice;
      if (!device) return [];

      const binHeight = Number(device.bin_height);
      const buffer = Number(device.height_buffer);
      if (!Number.isFinite(binHeight) || binHeight <= 0) return [];

      return this.telemetryRows
        .map((row) => {
          const rawDistance = Number(row.sensor_values?.fill_level);
          const value = rawDistance < 0 || !Number.isFinite(rawDistance)
            ? null
            : Math.max(0, Math.min(100, ((binHeight - (rawDistance - buffer)) / binHeight) * 100));

          return {
            x: this.formatDate(row.created_at),
            y: value,
          };
        })
        .filter((point) => point.y !== null);
    },

    renderChart() {
      const canvas = document.getElementById("telemetryChart");
      if (!canvas || typeof Chart === "undefined") return;

      const points = this.fillPercentagePoints();
      const labels = points.map((point) => point.x);
      const data = points.map((point) => point.y);

      if (this.chart) {
        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = data;
        this.chart.update();
        return;
      }

      this.chart = new Chart(canvas, {
        type: "line",
        data: {
          labels,
          datasets: [{
            label: "Fill %",
            data,
            borderColor: "#2563eb",
            backgroundColor: "rgba(37, 99, 235, 0.12)",
            borderWidth: 2,
            tension: 0.25,
            fill: true,
            pointRadius: 2,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            intersect: false,
            mode: "index",
          },
          scales: {
            y: {
              min: 0,
              max: 100,
              ticks: {
                callback: (value) => `${value}%`,
              },
            },
          },
        },
      });
    },

    formatDate(value) {
      if (!value) return "";
      return new Intl.DateTimeFormat(undefined, {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value));
    },
  };
}
