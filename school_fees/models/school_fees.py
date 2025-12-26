from odoo import models, fields, api, _
import base64
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    fichier_bin = fields.Binary(string="PDF File", attachment=True, help="Upload the binary file to convert.")
    
  
#fin diw
class StudentFeesRegister(models.Model):
    """Student fees Register"""

    _name = "student.fees.register"
    _description = "Student fees Register"

    """
    def unlink(self):
       
        for rec in self:
            if rec.state != "draft":
                raise ValidationError(
                    _(
                        "Vous ne pouvez pas supprimer un enregistrement confirmé ou en attente"
                    )
                )
        return super(StudentFeesRegister, self).unlink()

    """
    #diw
    academic_year_id = fields.Many2one(
        "academic.year",
        ondelete="restrict",
        string="Academic Session",
        default=lambda obj: obj.env["academic.year"].search(
            [("current", "=", True)]
        ),)

    year_date_start_s = fields.Char(string="Year Date Start", compute='_compute_year_date_start')
    year_date_stop_s = fields.Char(string="Year Date Stop", compute='_compute_year_date_stop')

    @api.depends('academic_year_id.date_start')
    def _compute_year_date_start(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_start:
                record.year_date_start_s = record.academic_year_id.date_start.year
            else:
                record.year_date_start_s = ''

    @api.depends('academic_year_id.date_stop')
    def _compute_year_date_stop(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_stop:
                record.year_date_stop_s = record.academic_year_id.date_stop.year
            else:
                record.year_date_stop_s = ''
                
    session = fields.Selection(
        [("premier_semestre", "1er semestre"),
            ("second_semestre", "2éme semestre"),
        ],"session", invisible="1")
    
    #

    total_amount_paid = fields.Float(
        "Total", compute="_compute_total_paid", help="Montant total payé"
    )
    @api.depends("line_ids")
    def _compute_total_paid(self):
        """Method to compute total amount"""
        for rec in self:
            total_amt = 0.0
            total_amt = sum(line.paid_amount for line in rec.line_ids)
            rec.total_amount_paid = total_amt


    total_amount = fields.Float(
        "Total", compute="_compute_total_amount", help="Fee total amounts"
    )
    @api.depends("line_ids")
    def _compute_total_amount(self):
        """Method to compute total amount"""
        for rec in self:
            total_amt = 0.0
            total_amt = sum(line.total for line in rec.line_ids)
            rec.total_amount = total_amt

    name = fields.Char("Name", required=True, help="Enter Name")
    date = fields.Date(
        "Date",
        required=True,
        help="Date of register",
        default=fields.Date.context_today,
    )
    number = fields.Char(
        "Number",
        readonly=True,
        default=lambda self: _("New"),
        help="Sequence number of fee registration form",
    )
    line_ids = fields.One2many(
        "student.payslip", "register_id", "PaySlips", help="Student payslips"
    )
    total_amount = fields.Float(
        "Total", compute="_compute_total_amount", help="Fee total amounts"
    )
    state = fields.Selection(
        [("draft", "Brouillon"), ("confirm", "Confirmé")],
        "State",
        readonly=True,
        default="draft",
        help="State of student fee registration form",
    )
    journal_id = fields.Many2one(
        "account.journal", "Journal", help="Select Journal", required=False
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        change_default=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        help="Select related company",
    )
    fees_structure = fields.Many2one(
        "student.fees.structure", "Fees Structure", help="Fee structure"
    )
    
   

    standard_id = fields.Many2one(
        "school.standard", "Class", help="Enter student standard"
    )

    def fees_register_draft(self):
        """Changes the state to draft"""
        self.state = "draft"

    
    def fees_register_confirm(self):
        """Méthode pour confirmer la fiche de paie et créer des factures dans les statistiques publiées"""
        stud_obj = self.env["student.student"]
        slip_obj = self.env["student.payslip"]
        move_obj = self.env["account.move"]
        
        for rec in self:
            if not rec.journal_id:
                raise ValidationError(_("Kindly, Select Account Journal!"))
            if not rec.fees_structure:
                raise ValidationError(_("Kindly, Select Fees Structure!"))

            # Vérifier si la structure de frais du registre est de type mensualité
            is_mensualite = rec.fees_structure.type_frais == 'mensualite'

            school_std_rec = rec.standard_id
            # Recherche de l'année académique en cours
            current_year = self.env['academic.year'].search([('current', '=', True)], limit=1)
            if not current_year:
                raise ValidationError(_("No current academic year is set. Please configure an academic.year with current=True."))

            # Chercher les étudiants de la classe et de l'année académique courante
            students_rec = stud_obj.search([
                ("standard_id", "=", school_std_rec.id),
                ("state", "=", "done"),
                ("year", "=", current_year.id),
            ])

            for stu in students_rec:
                old_slips_rec = slip_obj.search([
                    ("student_id", "=", stu.id),
                    ("date", "=", rec.date)
                ])
                
                if old_slips_rec:
                    raise ValidationError(_(
                        "There is already a Payslip exist for student: %s for same date!"
                    ) % stu.name)
                    
                rec.number = self.env["ir.sequence"].next_by_code(
                    "student.fees.register"
                ) or _("New")
                
                # Prendre la structure des frais de l'élève seulement si:
                # 1. C'est une mensualité (type_frais = 'mensualite')
                # 2. L'élève a une structure personnalisée (stu.type_mens)
                # 3. La structure personnalisée est différente de la structure par défaut
                if is_mensualite and stu.type_mens and stu.type_mens != rec.fees_structure:
                    fees_structure_id = stu.type_mens.id
                else:
                    fees_structure_id = rec.fees_structure.id

                res = {
                    "student_id": stu.id,
                    "register_id": rec.id,
                    "name": rec.name,
                    "date": rec.date,
                    "company_id": rec.company_id.id,
                    "currency_id": rec.company_id.currency_id.id or False,
                    "journal_id": rec.journal_id.id,
                    "fees_structure_id": fees_structure_id or False,
                }
                
                # Créer la fiche de paie
                slip_rec = slip_obj.create(res)
                slip_rec.onchange_student()
                
                # Confirmer la fiche de paie
                slip_rec.payslip_confirm()
                
                # Créer la facture directement en état posté
                partner = stu.partner_id
                invoice_vals = {
                    'partner_id': partner.id,
                    'invoice_date': rec.date,
                    'journal_id': rec.journal_id.id,
                    'ref': rec.name,
                    'move_type': 'out_invoice',
                    'student_payslip_id': slip_rec.id,
                }
                
                # Créer les lignes de facture
                invoice_lines = []
                for line in slip_rec.line_ids:
                    account_id = line.account_id.id if line.account_id else rec.journal_id.default_account_id.id
                    invoice_lines.append((0, 0, {
                        'name': line.name,
                        'account_id': account_id,
                        'quantity': 1.0,
                        'price_unit': line.amount,
                    }))
                
                invoice_vals['invoice_line_ids'] = invoice_lines
                
                # Créer et valider la facture
                invoice = move_obj.create(invoice_vals)
                invoice.action_post()
                
                # Lier la facture à la fiche de paie
                slip_rec.write({
                    'move_id': invoice.id,
                    'state': 'pending', 
                    'paid_amount': slip_rec.total,
                    'due_amount': 0.0,
                })

            # Calculate the amount
            amount = sum(data.total for data in rec.line_ids)
            rec.write({"total_amount": amount, "state": "confirm"})
                


    def action_view_payslips(self):
        """Ouvre la vue des fiches de paie liées à ce registre"""
        self.ensure_one()
        return {
            'name': _('Fiches de Paie'),
            'view_mode': 'tree,form',
            'res_model': 'student.payslip',
            'type': 'ir.actions.act_window',
            'domain': [('register_id', '=', self.id)],
            'context': {
                'default_register_id': self.id,
                'create': False,
            },
            'target': 'current',
        }

class StudentPayslipLine(models.Model):
    """Student PaySlip Line"""

    _name = "student.payslip.line"
    _description = "Student PaySlip Line"

    name = fields.Char("Name", required=True, help="Payslip")
    code = fields.Char("Code", required=True, help="Payslip code")
    type = fields.Selection(
        [("month", "Monthly"), ("year", "Yearly"), ("range", "Range")],
        "Duration",
        required=True,
        help="Select payslip type",
    )
    amount = fields.Float("Amount", digits=(16, 2), help="Fee amount")
    line_ids = fields.One2many(
        "student.payslip.line.line",
        "slipline_id",
        "Calculations",
        help="Payslip line",
    )
    slip_id = fields.Many2one(
        "student.payslip", "Pay Slip", help="Select student payslip"
    )
    description = fields.Text("Description", help="Description")
    company_id = fields.Many2one(
        "res.company",
        "Company",
        change_default=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )
    currency_id = fields.Many2one(
        "res.currency", "Currency", help="Select currency"
    )
    currency_symbol = fields.Char(
        related="currency_id.symbol", string="Symbol", help="Currency Symbol"
    )
    account_id = fields.Many2one(
        "account.account", "Account", help="Related account"
    )

    @api.onchange("company_id")
    def set_currency_onchange(self):
        """Onchange method to assign currency on change company"""
        for rec in self:
            rec.currency_id = rec.company_id.currency_id.id


class StudentFeesStructureLine(models.Model):
    """Student Fees Structure Line"""

    _name = "student.fees.structure.line"
    _description = "Student Fees Structure Line"
    _order = "sequence"

    name = fields.Char("Name", required=True, help="Enter fee structure name")
    code = fields.Char("Code", required=True, help="Fee structure code")
    type = fields.Selection(
        [("month", "Monthly"), ("year", "Yearly"), ("range", "Range")],
        "Duration",
        required=True,
        help="Fee structure type",
    )
    amount = fields.Float("Amount", digits=(16, 2), help="Fee amount")
    sequence = fields.Integer(
        "Sequence", help="Sequence of fee structure form"
    )
    line_ids = fields.One2many(
        "student.payslip.line.line",
        "slipline1_id",
        "Calculations",
        help="Student payslip line",
    )
    account_id = fields.Many2one("account.account", string="Account")
    company_id = fields.Many2one(
        "res.company",
        "Company",
        change_default=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )
    currency_id = fields.Many2one(
        "res.currency", "Currency", help="Select currency"
    )
    currency_symbol = fields.Char(
        related="currency_id.symbol",
        string="Symbol",
        help="Select currency symbol",
    )

    @api.onchange("company_id")
    def set_currency_company(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id.id


class StudentFeesStructure(models.Model):
    """Fees structure"""

    _name = "student.fees.structure"
    _description = "Student Fees Structure"

    type_frais = fields.Selection([
        ('mensualite', 'Mensualité'),
        ('inscription', 'Inscription'),
    ], string="Type de structure de frais", default="mensualite")
    

    name = fields.Char("Name", required=True, help="Fee structure name")
    code = fields.Char("Code", required=True, help="Fee structure code")
    line_ids = fields.Many2many(
        "student.fees.structure.line",
        "fees_structure_payslip_rel",
        "fees_id",
        "slip_id",
        "Fees Structure",
        help="Fee structure line",
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            """The code of the Fees Structure must be unique !""",
        )
    ]


class StudentPayslip(models.Model):
    _name = "student.payslip"
    _description = "Student PaySlip"


    #diw
    academic_year_id = fields.Many2one(
        "academic.year",
        ondelete="restrict",
        string="Academic Session",
        default=lambda obj: obj.env["academic.year"].search(
            [("current", "=", True)]
        ),)

    year_date_start_s = fields.Char(string="Year Date Start", compute='_compute_year_date_start')
    year_date_stop_s = fields.Char(string="Year Date Stop", compute='_compute_year_date_stop')

    @api.depends('academic_year_id.date_start')
    def _compute_year_date_start(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_start:
                record.year_date_start_s = record.academic_year_id.date_start.year
            else:
                record.year_date_start_s = ''

    @api.depends('academic_year_id.date_stop')
    def _compute_year_date_stop(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_stop:
                record.year_date_stop_s = record.academic_year_id.date_stop.year
            else:
                record.year_date_stop_s = ''
                
    session = fields.Selection(
        [("premier_semestre", "1er semestre"),
            ("second_semestre", "2éme semestre"),
        ],"session", invisible="1")
    
    #
    fees_structure_id = fields.Many2one(
        "student.fees.structure", "Fees Structure"
    )
    
    standard_id = fields.Many2one(
        "school.standard", "Class", help="Select school standard")
    
    division_id = fields.Many2one("standard.division", "Division", help="Select standard division")
    
    medium_id = fields.Many2one(
        "standard.medium", "Medium", help="Select standard medium"
    )
    
    register_id = fields.Many2one(
        "student.fees.register", "Register", help="Select student fee register"
    )
    
    name = fields.Char("Description", help="Payslip name")
    number = fields.Char(
        "Number",
        readonly=True,
        default=lambda self: _("/"),
        copy=False,
        help="Payslip number",
    )
    student_id = fields.Many2one(
        "student.student", "Student", required=True, help="Select student"
    )
    date = fields.Date(
        "Date",
        readonly=True,
        help="Current Date of payslip",
        default=fields.Date.context_today,
    )
    line_ids = fields.One2many(
        "student.payslip.line",
        "slip_id",
        "PaySlip Line",
        copy=False,
        help="Payslips",
    )
    total = fields.Monetary("Total", readonly=True, help="Total Amount")
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("confirm", "Confirmé"),
            ("pending", "En attente"),
            ("partial", "Partiel"),
            ("paid", "Payé"),
        ],
        "State",
        readonly=True,
        default="draft",
        help="State of the student payslip",
    )
    
   
    
    journal_id = fields.Many2one(
        "account.journal",
        "Journal",
        required=False,
        help="Select journal for account",
    )
    paid_amount = fields.Monetary("Paid Amount", help="Amount Paid")
    due_amount = fields.Monetary("Due Amount", help="Amount Remaining")
    currency_id = fields.Many2one(
        "res.currency", "Currency", help="Selelct currency"
    )
    currency_symbol = fields.Char(
        related="currency_id.symbol", string="Symbol", help="Currency symbol"
    )
    move_id = fields.Many2one(
        "account.move",
        "Journal Entry",
        readonly=True,
        ondelete="restrict",
        copy=False,
        help="Link to the automatically" "generated Journal Items.",
    )
    payment_date = fields.Date(
        "Payment Date",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Keep empty to use the current date",
    )
    type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("in_invoice", "Supplier Invoice"),
            ("out_refund", "Customer Refund"),
            ("in_refund", "Supplier Refund"),
        ],
        "Type",
        required=True,
        change_default=True,
        default="out_invoice",
        help="Payslip type",
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        change_default=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique(student_id,date,state)",
            "The code of the Fees Structure must be unique !",
        )
    ]

    

    @api.onchange("student_id")
    def onchange_student(self):
        """Method to get standard , division , medium of student selected"""
        if self.student_id:
            self.standard_id = self.student_id.standard_id.id or False
            self.division_id = (
                self.student_id.standard_id.division_id.id or False
            )
            self.medium_id = self.student_id.medium_id or False

    def unlink(self):
        """Inherited unlink method to check state at the record deletion"""
        for rec in self:
            if rec.state not in ("draft", "confirm", "pending"):
                raise ValidationError(
                    _("You can only delete records in draft, confirm or pending state!")
                )
        return super(StudentPayslip, self).unlink()

    @api.onchange("journal_id")
    def onchange_journal_id(self):
        """Method to get currency from journal"""
        for rec in self:
            journal = rec.journal_id
            currency_id = (
                journal
                and journal.currency_id
                and journal.currency_id.id
                or journal.company_id.currency_id.id
            )
            rec.currency_id = currency_id

    def _update_student_vals(self, vals):
        student_rec = self.env["student.student"].browse(
            vals.get("student_id")
        )
        vals.update(
            {
                "standard_id": student_rec.standard_id.id,
                "division_id": student_rec.standard_id.division_id.id,
                "medium_id": student_rec.medium_id.id,
            }
        )

    @api.model
    def create(self, vals):
        """Inherited create method to assign values from student model"""
        if vals.get("student_id"):
            self._update_student_vals(vals)
        return super(StudentPayslip, self).create(vals)

    def write(self, vals):
        """Inherited write method to update values from student model"""
        if vals.get("student_id"):
            self._update_student_vals(vals)
        return super(StudentPayslip, self).write(vals)

    def payslip_draft(self):
        """Change state to draft"""
        self.state = "draft"

    def payslip_paid(self):
        """Change state to paid"""
        self.state = "paid"

    def payslip_confirm(self):
        """Method to confirm payslip"""
        for rec in self:
            if not rec.journal_id:
                raise ValidationError(_("Kindly, Select Account Journal!"))
            if not rec.fees_structure_id:
                raise ValidationError(_("Kindly, Select Fees Structure!"))
            lines = []
            for data in rec.fees_structure_id.line_ids or []:
                line_vals = {
                    "slip_id": rec.id,
                    "name": data.name,
                    "code": data.code,
                    "type": data.type,
                    "account_id": data.account_id.id,
                    "amount": data.amount,
                    "currency_id": data.currency_id.id or False,
                    "currency_symbol": data.currency_symbol or False,
                }
                lines.append((0, 0, line_vals))
            rec.write({"line_ids": lines})
            # Compute amount
            amount = 0
            amount = sum(data.amount for data in rec.line_ids)
            rec.register_id.write({"total_amount": rec.total})
            rec.write(
                {
                    "total": amount,
                    "state": "confirm",
                    "due_amount": amount,
                    "currency_id": rec.company_id.currency_id.id or False,
                }
            )

    def invoice_view(self):
        """View number of invoice of student"""
        invoice_obj = self.env["account.move"]
        for rec in self:
            invoices_rec = invoice_obj.search(
                [("student_payslip_id", "=", rec.id)]
            )
            action = rec.env.ref(
                "account.action_move_out_invoice_type"
            ).read()[0]
            if len(invoices_rec) > 1:
                action["domain"] = [("id", "in", invoices_rec.ids)]
            elif len(invoices_rec) == 1:
                action["views"] = [
                    (rec.env.ref("account.view_move_form").id, "form")
                ]
                action["res_id"] = invoices_rec.ids[0]
            else:
                action = {"type": "ir.actions.act_window_close"}
        return action

    def action_move_create(self):
        cur_obj = self.env["res.currency"]
        move_obj = self.env["account.move"]
        move_line_obj = self.env["account.move.line"]
        for fees in self:
            if not fees.journal_id.sequence_id:
                raise ValidationError(
                    _(
                        """
            Please define sequence on the journal related to this invoice."""
                    )
                )
            # field 'centralisation' from account.journal
            #  is deprecated field since v9
            if fees.move_id:
                continue
            ctx = self._context.copy()
            ctx.update({"lang": fees.student_id.lang})
            if not fees.payment_date:
                self.write([fees.id], {"payment_date": fields.Date.today()})
            company_currency = fees.company_id.currency_id.id
            diff_currency_p = fees.currency_id.id != company_currency
            current_currency = (
                fees.currency_id and fees.currency_id.id or company_currency
            )
            account_id = False
            comapny_ac_id = False
            if fees.type in ("in_invoice", "out_refund"):
                account_id = fees.student_id.property_account_payable.id
                cmpy_id = fees.company_id.partner_id
                comapny_ac_id = cmpy_id.property_account_receivable.id
            elif fees.type in ("out_invoice", "in_refund"):
                account_id = fees.student_id.property_account_receivable.id
                cmp_id = fees.company_id.partner_id
                comapny_ac_id = cmp_id.property_account_payable.id
            move = {
                "ref": fees.name,
                "journal_id": fees.journal_id.id,
                "date": fees.payment_date or fields.Date.today(),
            }
            ctx.update({"company_id": fees.company_id.id})
            move_id = move_obj.create(move)
            context_multi_currency = self._context.copy()
            context_multi_currency.update({"date": fields.Date.today()})
            debit = 0.0
            credit = 0.0
            if fees.type in ("in_invoice", "out_refund"):
                # compute method from res.currency is deprecated
                #    since v12 and replaced with _convert
                credit = cur_obj._convert(
                    fees.total, company_currency, fees.company_id, self.date
                )
            elif fees.type in ("out_invoice", "in_refund"):
                debit = cur_obj._convert(
                    fees.total, company_currency, fees.company_id, self.date
                )
            if debit < 0:
                credit = -debit
                debit = 0.0
            if credit < 0:
                debit = -credit
                credit = 0.0
            sign = debit - credit < 0 and -1 or 1
            cr_id = diff_currency_p and current_currency or False
            am_cr = diff_currency_p and sign * fees.total or 0.0
            date = fees.payment_date or fields.Date.today()
            move_line = {
                "name": fees.name or "/",
                "move_id": move_id,
                "debit": debit,
                "credit": credit,
                "account_id": account_id,
                "journal_id": fees.journal_id.id,
                "parent_id": fees.student_id.parent_id.id,
                "currency_id": cr_id,
                "amount_currency": am_cr,
                "date": date,
            }
            move_line_obj.create(move_line)
            cr_id = diff_currency_p and current_currency or False
            move_line = {
                "name": fees.name or "/",
                "move_id": move_id,
                "debit": credit,
                "credit": debit,
                "account_id": comapny_ac_id,
                "journal_id": fees.journal_id.id,
                "parent_id": fees.student_id.parent_id.id,
                "currency_id": cr_id,
                "amount_currency": am_cr,
                "date": date,
            }
            move_line_obj.create(move_line)
            fees.write({"move_id": move_id})
            move_obj.action_post([move_id])

    def student_pay_fees(self):
        """Generate invoice of student fee"""
        sequence_obj = self.env["ir.sequence"]
        for rec in self:
            if rec.number == "/":
                rec.number = sequence_obj.next_by_code("student.payslip") or _(
                    "New"
                )
            rec.state = "pending"
            partner = rec.student_id and rec.student_id.partner_id
            vals = {
                "partner_id": partner.id,
                "invoice_date": rec.date,
                "journal_id": rec.journal_id.id,
                "name": rec.number,
                "student_payslip_id": rec.id,
                "move_type": "out_invoice",
            }
            invoice_line = []
            for line in rec.line_ids:
                acc_id = ""
                if line.account_id.id:
                    acc_id = line.account_id.id
                else:
                    #     replaced / deprecated fields of v13:
                    #     default_debit_account_id,
                    #     default_credit_account_id from account.journal
                    acc_id = rec.journal_id.default_account_id.id
                invoice_line_vals = {
                    "name": line.name,
                    "account_id": acc_id,
                    "quantity": 1.000,
                    "price_unit": line.amount,
                }
                invoice_line.append((0, 0, invoice_line_vals))
            vals.update({"invoice_line_ids": invoice_line})
            # creates invoice
            account_invoice_id = self.env["account.move"].create(vals)
            #diw: mettre à jour du champ move_id avec l'ID de la facture nouvellement créée
            rec.move_id = account_invoice_id
            invoice_obj = self.env.ref("account.view_move_form")
            return {
                "name": _("Pay Fees"),
                "view_mode": "form",
                "res_model": "account.move",
                "view_id": invoice_obj.id,
                "type": "ir.actions.act_window",
                "nodestroy": True,
                "target": "current",
                "res_id": account_invoice_id.id,
                "context": {},
            }


class StudentPayslipLineLine(models.Model):
    """Function Line."""

    _name = "student.payslip.line.line"
    _description = "Function Line"
    _order = "sequence"

    slipline_id = fields.Many2one(
        "student.payslip.line", "Slip Line Ref", help="Student payslip line"
    )
    slipline1_id = fields.Many2one(
        "student.fees.structure.line", "Slip Line", help="Student payslip line"
    )
    sequence = fields.Integer("Sequence", help="Sequence of payslip")
    from_month = fields.Many2one(
        "academic.month", "From Month", help="Academic starting month"
    )
    to_month = fields.Many2one(
        "academic.month", "To Month", help="Academic end month"
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    student_payslip_id = fields.Many2one(
        "student.payslip",
        string="Student Payslip",
        help="Select student payslip",
    )

    

    trigger_payslip_update = fields.Boolean(compute='_compute_trigger_payslip_update')

    @api.depends('payment_state', 'amount_total', 'amount_residual')
    def _compute_trigger_payslip_update(self):
        for move in self:
            if move.student_payslip_id:
                try:
                    # Mettre à jour les montants dans le payslip
                    paid_amount = move.amount_total - move.amount_residual
                    move.student_payslip_id.write({
                        'paid_amount': paid_amount,
                        'due_amount': move.amount_residual,
                        'total': move.amount_total
                    })
                    
                    # Mettre à jour l'état du payslip
                    if move.payment_state == 'paid':
                        move.trigger_payslip_update = True
                        move.student_payslip_id.write({'state': 'paid'})
                    elif move.payment_state == 'partial':
                        move.trigger_payslip_update = False
                        move.student_payslip_id.write({'state': 'partial'})    
                    elif move.payment_state == 'not_paid':
                        move.trigger_payslip_update = False
                        move.student_payslip_id.write({'state': 'pending'})
                    else:
                        move.trigger_payslip_update = False
                except Exception as e:
                    raise ValidationError(_('Failed to update payslip: %s') % str(e))
            else:
                move.trigger_payslip_update = False    

      
    #fin diw
    
    #diw
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        change_default=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )
     
    academic_year_id = fields.Many2one(
        "academic.year",
        ondelete="restrict",
        string="Academic Session",
        default=lambda obj: obj.env["academic.year"].search(
            [("current", "=", True)]),)

    year_date_start_s = fields.Char(string="Year Date Start", compute='_compute_year_date_start')
    year_date_stop_s = fields.Char(string="Year Date Stop", compute='_compute_year_date_stop')

    @api.depends('academic_year_id.date_start')
    def _compute_year_date_start(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_start:
                record.year_date_start_s = record.academic_year_id.date_start.year
            else:
                record.year_date_start_s = ''

    @api.depends('academic_year_id.date_stop')
    def _compute_year_date_stop(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_stop:
                record.year_date_stop_s = record.academic_year_id.date_stop.year
            else:
                record.year_date_stop_s = ''
                
    session = fields.Selection(
        [("premier_semestre", "1er semestre"),
            ("second_semestre", "2éme semestre"),
        ],"session", invisible="1")
    
    mois_paiement = fields.Char(
        "Mois de paiement",
        readonly=True,
        compute='_compute_mois_paiement',
        store=True,
        help="Mois de paiement extrait de la date du student.payslip (format: janvier, février...)"
    )

    @api.depends('student_payslip_id.date')
    def _compute_mois_paiement(self):
        # Import de la librairie locale pour les mois en français
        from datetime import datetime
        month_names = {
            1: "janvier",
            2: "février",
            3: "mars",
            4: "avril",
            5: "mai",
            6: "juin",
            7: "juillet",
            8: "août",
            9: "septembre",
            10: "octobre",
            11: "novembre",
            12: "décembre"
        }
        
        for move in self:
            if move.student_payslip_id and move.student_payslip_id.date:
                month_num = move.student_payslip_id.date.month
                move.mois_paiement = month_names.get(month_num, "")
            else:
                move.mois_paiement = False
    #


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        """Method to change state to paid when state in invoice is paid"""
        res = super(AccountPayment, self).action_post()
        curr_date = fields.Date.today()
        vals = {}
        for rec in self:
            invoice = rec.move_id
            #        'invoice_ids' deprecated field instead of this
            #                             used delegation with account_move
            vals.update({"due_amount": invoice.amount_residual})
            if invoice.student_payslip_id and invoice.payment_state == "paid":
                # Calculate paid amount and changes state to paid
                fees_payment = (
                    invoice.student_payslip_id.paid_amount + rec.amount
                )
                vals.update(
                    {
                        "state": "paid",
                        "payment_date": curr_date,
                        "move_id": invoice.id or False,
                        "paid_amount": fees_payment,
                        "due_amount": invoice.amount_residual,
                    }
                )
            if (
                invoice.student_payslip_id
                and invoice.payment_state == "not_paid"
            ):
                # Calculate paid amount and due amount and changes state
                # to pending
                fees_payment = (
                    invoice.student_payslip_id.paid_amount + rec.amount
                )
                vals.update(
                    {
                        "state": "pending",
                        "due_amount": invoice.amount_residual,
                        "paid_amount": fees_payment,
                    }
                )
            invoice.student_payslip_id.write(vals)
        return res


class StudentFees(models.Model):
    _inherit = "student.student"
    
    
    type_mens = fields.Many2one('student.fees.structure', 'Type de mensualité')

    
    type_frais = fields.Selection([
        ('mensualite', 'Mensualité'),
        ('inscription', 'Inscription'),
    ], string="Type de structure de frais", default="mensualite", related="type_mens.type_frais")
    

    def set_alumni(self):
        """Override method to raise warning when fees payment of student is
        remaining when student set to alumni state"""
        student_payslip_obj = self.env["student.payslip"]
        for rec in self:
            student_fees_rec = student_payslip_obj.search(
                [
                    ("student_id", "=", rec.id),
                    ("state", "in", ["confirm", "pending"]),
                ]
            )
            if student_fees_rec:
                raise ValidationError(
                    _(
                        """
You cannot alumni student because payment of fees of student is remaining!"""
                    )
                )
            return super(StudentFees, self).set_alumni()
