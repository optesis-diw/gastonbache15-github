# See LICENSE file for full copyright and licensing details.

{
    "name": "Exam Management for Education ERP",
    "version": "14.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "School Management",
    "license": "AGPL-3",
    "summary": "A Module For Exams Management Taken In School",
    "complexity": "easy",
    "images": ["static/description/exam_banner.png"],
    "depends": ["school", "timetable"],
    "data": [
        "security/exam_security.xml",
        "security/ir.model.access.csv",
        "data/exam_sequence.xml",
        "views/exam_view.xml",
        "report/exam_result_report.xml",
        "report/additional_exam_report.xml",
        "report/result_information_report.xml",
        "report/batch_exam.xml",
        "report/custom_external_layout_bulletin.xml",
        "report/report_view.xml",
        "wizard/subject_result.xml",
        "wizard/batch_result.xml",

	"report/releve_exam.xml",
    ],
    "demo": ["demo/exam_demo.xml"],
    "installable": True,
    "application": True,
}
