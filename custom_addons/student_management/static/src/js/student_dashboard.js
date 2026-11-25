import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    Component,
    onWillStart,
    onMounted,
    onWillUnmount,
    useRef,
} from "@odoo/owl";

import { loadJS } from "@web/core/assets";

class StudentDashboard extends Component {
    static template = "student_management.StudentDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.refs = {
            students: useRef("students"),
            teachers: useRef("teachers"),
            standards: useRef("standards"),
            subjects: useRef("subjects"),
            marksheets: useRef("marksheets"),
        };

        this.charts = [];

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");

            this.data = await this.orm.call(
                "student.dashboard",
                "get_dashboard_graph_data",
                []
            );
        });

        onMounted(() => this.renderCharts());

        onWillUnmount(() => {
            this.charts.forEach(chart => chart.destroy());
        });
    }

    renderCharts() {
        const definitions = [
            ["students", "All Students", "student.management"],
            ["teachers", "All Teachers", "student.teacher"],
            ["standards", "All Standards", "student.standard"],
            ["subjects", "All Subjects", "student.subject"],
            ["marksheets", "All Marksheets", "student.marks.sheet"],
        ];

        for (const [key, label, model] of definitions) {
            const canvas = this.refs[key].el;

            if (!canvas) continue;

            const chart = new window.Chart(canvas, {
                type: "bar",
                data: {
                    labels: ["Total"],
                    datasets: [{
                        label: label,
                        data: [this.data[key]],
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: () => {
                        this.action.doAction({
                            type: "ir.actions.act_window",
                            name: label,
                            res_model: model,
                            views: [[false, "list"], [false, "form"]],
                            target: "current",
                        });
                    },
                },
            });

            this.charts.push(chart);
        }
    }
}

registry.category("actions").add(
    "student_management_dashboard",
    StudentDashboard
);
