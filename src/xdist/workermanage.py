import fnmatch
import time
import os
import re
import sys
import uuid
from pathlib import Path
from typing import List, Union, Sequence, Optional, Any, Tuple, Set

import pytest
import execnet

import xdist.remote
from xdist.remote import Producer
from xdist.plugin import _sys_path


def parse_spec_config(config):
    xspeclist = []
    for xspec in config.getvalue("tx"):
        i = xspec.find("*")
        try:
            num = int(xspec[:i])
        except ValueError:
            xspeclist.append(xspec)
        else:
            xspeclist.extend([xspec[i + 1 :]] * num)
    if not xspeclist:
        raise pytest.UsageError(
            "MISSING test execution (tx) nodes: please specify --tx"
        )
    return xspeclist


class NodeManager:
    EXIT_TIMEOUT = 10
    DEFAULT_IGNORES = [".*", "*.pyc", "*.pyo", "*~"]

    def __init__(self, config, specs=None, defaultchdir="pyexecnetcache") -> None:
        self.config = config
        self.trace = self.config.trace.get("nodemanager")
        self.testrunuid = self.config.getoption("testrunuid")
        if self.testrunuid is None:
            self.testrunuid = uuid.uuid4().hex
        self.group = execnet.Group()
        if specs is None:
            specs = self._getxspecs()
        self.specs = []
        for spec in specs:
            if not isinstance(spec, execnet.XSpec):
                spec = execnet.XSpec(spec)
            if not spec.chdir and not spec.popen:
                spec.chdir = defaultchdir
            self.group.allocate_id(spec)
            self.specs.append(spec)
        self.roots = self._getrsyncdirs()
        self.rsyncoptions = self._getrsyncoptions()
        self._rsynced_specs: Set[Tuple[Any, Any]] = set()
        self.log = Producer(f"node-manager", enabled=config.option.debug)
        paths = [
            [
                "tests/test_bill_pay/test_services/test_services.py",
                "tests/test_fixtures/test_load_test/test_reimbursements.py",
                "tests/test_business/test_api/test_admin_delete_department.py",
                "tests/test_growth_intelligence/test_services.py",
                "tests/test_flex/test_admin_api/test_fee_components.py",
                "tests/test_profile/test_api/test_user_change_password.py",
                "tests/test_reimbursement/test_schema.py",
                "tests/test_profile/test_api/test_existing_identity.py",
                "tests/test_receipt/test_date_extractor.py",
                "tests/test_internal_tooling/test_cohere_integration/test_tasks.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_filtered_accounting_codes_opportunity.py",
                "tests/test_async_job/test_routes.py",
                "tests/test_banking/test_api/test_update_manual_bank_connections.py",
                "tests/test_qbr/services/test_is_business_eligible_for_qbr.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_loan_origination/test_services/test_loan_state_machine.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_bill_pay/test_api/test_public_api.py",
                "tests/test_backfills/instances/test_backfill_limit_amounts_for_mismatched_transactions_20230607231414.py",
                "tests/test_flex/test_public_api/test_installment_payment_range.py",
                "tests/test_developer/test_receipt/test_receipt_api.py",
                "tests/test_spend_allocations/test_dao/test_spend_allocation_spend_event_mapping.py",
                "tests/test_statement/test_services/test_limit_checks.py",
                "tests/test_transaction/test_schemas.py",
                "tests/test_configuration/test_api.py",
                "tests/test_business/test_api/test_admin_delete_department.py",
                "tests/test_banking/test_api/test_get_transaction_categorization.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_delinquency/test_admin_api.py",
                "tests/test_incentives/test_utils.py",
                "tests/test_bill_pay/test_services/test_accounting_schema.py",
                "tests/test_banking/test_api/test_upload_manual_bank_statement.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_gmail_integration_opportunity.py",
                "tests/test_communication/test_api/test_slack_preference_override.py",
                "tests/test_banking/test_api/test_bank_statement_parse.py",
                "tests/test_alerts/test_dao.py",
                "tests/test_async_job/test_routes.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_financing_application/test_api/test_post_submit.py",
                "tests/test_transaction/test_api/test_bill_matches.py",
                "tests/test_incentives/test_api/test_admin_api.py",
                "tests/test_flex/test_celery_tasks/test_fa_daily_summary.py",
                "tests/test_business/test_api/test_change_roles.py",
                "tests/test_celery/test_communicate/test_communicate_business_merchant_restrictions_updated.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_interpret/test_heuristic_analysis.py",
                "tests/test_transaction/test_schemas.py",
                "tests/test_business/test_api/test_admin_bulk_change_department_location.py",
                "tests/test_ecommerce/test_api/test_public_api.py",
                "tests/test_growth_intelligence/test_services.py",
                "tests/test_celery/test_banking/test_heron/test_poll_long_processing_batch.py",
                "tests/test_profile/test_api/test_user_change_password.py",
                "tests/test_reimbursement/test_schema.py",
                "tests/test_profile/test_api/test_existing_identity.py",
                "tests/test_receipt/test_date_extractor.py",
                "tests/test_in_app_onboarding/test_first_spend_services.py",
                "tests/test_stripe/test_db_routines/test_new_stripe_transaction.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_billing/test_services/test_create_active_or_trial_subscription.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_banking/test_api/test_update_manual_bank_connections.py",
                "tests/test_qbr/services/test_is_business_eligible_for_qbr.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_loan_origination/test_services/test_loan_state_machine.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_reimbursement/test_api/test_public_api.py",
                "tests/test_billing/test_dao/test_transaction.py",
                "tests/test_receipt_integrations/test_uber/test_dao.py",
                "tests/test_rules_engine/test_dao.py",
                "tests/test_banking/test_heron_integration/test_heron_services.py",
                "tests/test_transaction/test_services/test_dispute_utils.py",
                "tests/test_celery/test_communicate/test_request_transaction_receipt.py",
                "tests/test_accounting/test_sync/test_list_tracking_category_resources.py",
                "tests/test_backfills/instances/test_backfill_compliance_definitions_20230622174414.py",
                "tests/test_celery/test_payee/test_document_tasks.py",
                "tests/test_celery/test_slack_communication/test_update_slack_reimbursement_request_to_manager.py",
                "tests/test_payments/test_services/test_risk.py",
                "tests/test_flex/test_public_api/test_risk_holds.py",
                "tests/test_banking/test_utils.py",
                "tests/test_ledger/test_internal/test_dao/test_balances.py",
                "tests/test_webhooks/test_email_dao.py",
                "tests/test_banking/test_api/test_admin_api_financial_accounts.py",
                "tests/test_accounting/test_filters/test_apis/test_display_tracking_category_options.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_accounting_opportunity.py",
                "tests/test_business/test_api/test_admin_mq_to_stripe_migration.py",
                "tests/test_celery/test_communicate/test_communicate_to_admin_email_integration_enabled.py",
                "tests/test_profile/test_api/test_slack_email_address.py",
                "tests/test_spend/test_admin_api.py",
                "tests/test_profile/test_api/test_user_preferences.py",
                "tests/test_banking/test_api/test_bank_account_subtype_update.py",
                "tests/test_accounting/test_providers/test_sage/test_provider_context.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_accounting/test_lists/test_apis/test_cardholder_can_select_none.py",
                "tests/test_docs/test_restx.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_transaction/test_api/test_list_transactions.py",
                "tests/test_spend_request/test_tasks.py",
                "tests/test_receipt/test_text_based_match/test_text_based_match.py",
                "tests/test_internal_tooling/test_operational_definitions/test_card/test_dao.py",
                "tests/test_alerts/test_utils.py",
                "tests/test_transaction/test_api/test_memo_in_transaction.py",
                "tests/test_banking/test_api/test_business_manual_bank_account_setup.py",
                "tests/test_transaction/test_services/test_transaction_services.py",
                "tests/test_business/test_api/test_create_card_branding.py",
                "tests/test_fraud/test_reimbursement_fraud_rules.py",
                "tests/test_receipt_integrations/test_amazon/test_receipt_generation.py",
                "tests/test_spend/test_dao.py",
                "tests/test_checklist/test_checkers/test_checker_kyc_business_passing.py",
                "tests/test_profile/test_models/test_user.py",
                "tests/test_growth_intelligence/test_services.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_interpret/test_interpret.py",
                "tests/test_webhooks/test_email_dao.py",
                "tests/test_banking/test_api/test_list_institutions.py",
                "tests/test_banking/test_models.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_gmail_integration_opportunity.py",
                "tests/test_communication/test_api/test_slack_preference_override.py",
                "tests/test_communication_platform/test_clients/test_push_notification_client.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_communication/test_api/test_notify_by_push_notification_admin.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_external_firm/test_external_firm_application_model.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_spend_allocations/test_api/test_public_api.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_card_rule_opportunity.py",
                "tests/test_statement/test_formatters/test_csv_formatter.py",
                "tests/test_transaction_interactions/test_admin_api.py",
                "tests/test_internal_tooling/test_operational_definitions/test_card/test_dao.py",
                "tests/test_flex/test_celery_tasks/test_check_balance_sheet_utilization.py",
                "tests/test_transaction/test_api/test_bill_matches.py",
                "tests/test_developer/test_user/test_celery.py",
                "tests/test_stale_gla/test_communication.py",
                "tests/test_flex/test_celery_tasks/test_unlinked_bills_email.py",
                "tests/test_invite/test_api/test_create_invite_with_approval_policies.py",
                "tests/test_celery/test_communicate/test_communicate_submitter_daily_approved_reimbursements.py",
                "tests/test_flex/test_dao/test_get_selected_flex_offers.py",
                "tests/test_proxies/test_sentilink.py",
                "tests/test_fixtures/test_load_test/test_users.py",
                "tests/test_stripe/test_card_transitions.py",
                "tests/test_checklist/test_checkers/test_checker_accounting_data_verified.py",
                "tests/test_webhooks/test_comply_advantage.py",
                "tests/test_profile/test_api/test_session_revocation_and_signout.py",
                "tests/test_flex/test_dao/test_flex_payment_transfer.py",
                "tests/test_transfer/test_models.py",
                "tests/test_fraud/test_admin_api/test_whitelist_card_for_3ds.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_celery/test_banking/test_manual_transaction_tasks.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_okta_scim/test_dao.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py"
            ],
            [
                "tests/test_celery/test_bill_pay_tasks.py",
                "tests/test_celery/test_accounting_reports_tasks.py",
                "tests/test_accounting/test_match_card_to_bill/test_public_api.py",
                "tests/test_spend_allocations/test_api/test_spend_allocations_history.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_interpret/test_chargebacks.py",
                "tests/test_communication/test_slack_communication/test_communicate_receipt_success.py",
                "tests/test_communication/test_api/test_user_initiated_comms.py",
                "tests/test_business/test_api/test_admin_business_detail.py",
                "tests/test_developer/test_dao.py",
                "tests/test_transfer/test_dao.py",
                "tests/test_fraud/test_transaction/test_confirm_transaction_is_not_fraud.py",
                "tests/test_profile/test_api/test_set_phone_number.py",
                "tests/test_switching/test_api/test_admin_api.py",
                "tests/test_transaction/test_dao/test_sort.py",
                "tests/test_celery/test_communicate/test_communicate_business_merchant_restrictions_updated.py",
                "tests/test_banking/test_api/test_user_bank_account.py",
                "tests/test_stripe/test_stripe_ofac.py",
                "tests/test_referral/test_model.py",
                "tests/test_payee/test_tasks/test_send_renewal_reminder.py",
                "tests/test_magic_link/test_admin_api.py",
                "tests/test_receipt/_internal/matching/test_merchant_specific_matching.py",
                "tests/test_accounting/test_reports/test_dao.py",
                "tests/test_fixtures/test_fixture_users.py",
                "tests/test_negotiations/api/test_admin_api.py",
                "tests/test_issuing/test_services/test_issuing_business.py",
                "tests/test_partner_rewards/test_dao.py",
                "tests/test_delinquency/test_tasks.py",
                "tests/test_invoices/test_tasks.py",
                "tests/test_billing/test_services/test_decorators.py",
                "tests/test_balance/test_services/test_get_all_limits_for_businesses.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py"
            ],
            [
                "tests/test_webhooks/test_twilio_webhooks.py",
                "tests/test_banking/test_api/test_debit_check_endpoints.py",
                "tests/test_accounting/test_cache/test_accounting_resolution_cache.py",
                "tests/test_flex/test_public_api/test_list_flex.py",
                "tests/test_accounting/test_api/test_advanced_rules.py",
                "tests/test_flex/test_celery_tasks/test_send_reminder_for_ineligible_flex_bills.py",
                "tests/test_celery/test_communicate/test_communicate_invitation_events.py",
                "tests/test_card/test_api/test_admin_card_details.py",
                "tests/test_flex/test_services/test_initiate_payment_for_installment.py",
                "tests/test_flex/test_celery_tasks/test_post_daily_summary.py",
                "tests/test_developer/test_spend_program/test_spend_program_api.py",
                "tests/test_accounting/test_csv_generator.py",
                "tests/test_accounting/test_command_center/test_dao.py",
                "tests/test_celery/test_slack_communication/test_communicate_new_reimbursement.py",
                "tests/test_travel/test_services.py",
                "tests/test_developer/test_custom_id_provider/test_custom_id_api.py",
                "tests/test_checklist/test_checkers/test_checker_no_unresolved_exceptions.py",
                "tests/test_flex/test_public_api/test_estimated_fees_for_business.py",
                "tests/test_transfer/test_api/test_admin_cancel_transfer.py",
                "tests/test_accounting/test_lists/test_apis/test_reimbursement_default_vendor.py",
                "tests/test_payments/test_services/test_risk.py",
                "tests/test_accounting/test_mapping/test_schema_transformers.py",
                "tests/test_webhooks/test_comply_advantage.py",
                "tests/test_accounting/test_platform/test_dao.py",
                "tests/test_qbr/test_opportunities/test_compliance_opportunities/test_travel_policy_opportunity.py",
                "tests/test_transfer/test_models.py",
                "tests/test_fraud/test_admin_api/test_whitelist_card_for_3ds.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_wallet/test_public_api/test_business_entity_wallet_account.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_okta_scim/test_dao.py",
                "tests/test_authz/test_models.py",
                "tests/test_receipt_integrations/test_uber/celery/test_tasks.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_loan_origination/test_services/test_loan_state_machine.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py"
            ],
            [
                "tests/test_approval_policy/api/test_public_api.py",
                "tests/test_metrics/test_spend/test_dao.py",
                "tests/test_celery/test_banking/test_notification_sift_tasks.py",
                "tests/test_billing/test_products/test_reimbursements.py",
                "tests/test_profile/test_api/test_sign_up.py",
                "tests/test_payments/test_services/test_core.py",
                "tests/test_savings/test_services/test_persist_insights.py",
                "tests/test_spend_allocations/test_api/test_spend_allocation_renaming.py",
                "tests/test_accounting/test_providers/test_sage/test_client.py",
                "tests/test_spend_request/test_dao/test_spend_request.py",
                "tests/test_flex/test_public_api/test_get_flex_by_uuid.py",
                "tests/test_developer/test_memo/test_memo_api.py",
                "tests/test_authentication/test_services.py",
                "tests/test_webhooks/test_receipt_email_webhooks.py",
                "tests/test_flex/test_celery_tasks/test_fa_daily_summary.py",
                "tests/test_celery/test_business_tasks.py",
                "tests/test_magic_link/test_vendor_upload_payment_details.py",
                "tests/test_profile/test_api/test_set_date_of_birth.py",
                "tests/test_celery/test_communicate/test_communicate_new_statement.py",
                "tests/test_workflows/test_services/test_conditions.py",
                "tests/test_checklist/test_checkers/test_checker_passes_underwriting.py",
                "tests/test_webhooks/test_scale.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_celery/test_slack_communication/test_communicate_weekly_reminder.py",
                "tests/test_celery/test_communicate/test_communicate_monthly_spend_report.py",
                "tests/test_business/test_api/test_auth_total_resource_count.py",
                "tests/test_profile/test_api/test_is_sso_required.py",
                "tests/test_communication/test_services.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_invoices/test_tasks.py",
                "tests/test_billing/test_services/test_decorators.py",
                "tests/test_customer/test_api/test_sftp_transaction_upload.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_spend/test_spend_events/test_bill_pay_service.py",
                "tests/test_stripe/test_stripe_dao.py",
                "tests/test_profile/test_api/test_list_users.py",
                "tests/test_docs/test_valid_openapi.py",
                "tests/test_bill_pay/test_api/test_admin_api.py",
                "tests/test_flex/test_public_api/test_update_bank_account.py",
                "tests/test_metrics/test_transaction_metrics/test_get_transaction_metrics.py",
                "tests/test_hris/test_continuous_sync.py",
                "tests/test_transfer/test_api/test_make_payment.py",
                "tests/test_referral/test_api/test_admin_api.py",
                "tests/test_receipt/test_api/test_admin_inbox.py",
                "tests/test_business/test_api/test_change_direct_manager.py",
                "tests/test_authentication/test_services.py",
                "tests/test_celery/financing_application/test_middesk_tasks.py",
                "tests/test_switching/test_api/test_admin_api.py",
                "tests/test_magic_link/test_services.py",
                "tests/test_checklist/test_checkers/test_checker_can_give_requested_limit.py",
                "tests/test_transaction/test_api/test_list_transaction_interactions.py",
                "tests/test_stripe/test_stripe_ofac.py",
                "tests/test_transaction/test_api/test_currency_conversion.py",
                "tests/test_hris/test_invite_utils.py",
                "tests/test_magic_link/test_admin_api.py",
                "tests/test_receipt/_internal/matching/test_merchant_specific_matching.py",
                "tests/test_delinquency/test_admin_api.py",
                "tests/test_banking/test_api/test_business_bank_account_queue.py",
                "tests/test_negotiations/api/test_admin_api.py",
                "tests/test_okta_scim/test_tasks.py",
                "tests/test_partner_rewards/test_dao.py",
                "tests/test_delinquency/test_tasks.py",
                "tests/test_qbr/test_opportunities/test_compliance_opportunities/test_submission_policy_opportunity.py",
                "tests/test_billing/test_services/test_decorators.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_bill_pay_opportunity.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_checklist/test_evaluate_checklist.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_transaction/test_query/test_core.py",
                "tests/test_developer/test_card/test_card_api.py",
                "tests/test_accounting/test_attribution/test_accounting_transaction_query.py",
                "tests/test_stripe/test_currency_conversion_fee.py",
                "tests/test_card_programs/test_public_api.py",
                "tests/test_accounting/test_sync/test_utils.py",
                "tests/test_accounting/test_mapping/test_schemas.py",
                "tests/test_capital_markets/test_admin_api.py",
                "tests/test_bill_pay/test_api/test_vendor_import_api.py",
                "tests/test_business/test_entity/test_public_api.py",
                "tests/test_advisor_console/public_api/test_authorizations_resource.py",
                "tests/test_external_firm/routes/public_api/test_public_referral_routes.py",
                "tests/test_celery/test_document_upload_requests.py",
                "tests/test_financing_application/test_api/test_evaluate_checklist_for_fa.py",
                "tests/test_profile/test_api/test_account_setup.py",
                "tests/test_accounting/test_schemas.py",
                "tests/test_celery/test_communicate/test_communicate_upcoming_debit.py",
                "tests/test_checklist/test_checkers/test_checker_no_unresolved_exceptions.py",
                "tests/test_flex/test_dao/test_get_selected_flex_offers.py",
                "tests/test_fraud/test_soft_decline.py",
                "tests/test_profile/test_api/test_passwordless_link_login.py",
                "tests/test_qbr/public_api/test_reports_resource.py",
                "tests/test_webhooks/marqeta/test_api/test_tokenization.py",
                "tests/test_card/test_dao/test_cards_for_identity.py",
                "tests/test_profile/test_api/test_session_revocation_and_signout.py",
                "tests/test_spend_allocations/test_dao/test_create_category_restrictions_exemption.py",
                "tests/test_banking/test_models.py",
                "tests/test_fraud/test_admin_api/test_whitelist_card_for_3ds.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_celery/test_banking/test_manual_transaction_tasks.py",
                "tests/test_banking/test_api/test_legal_terms.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_profile/test_api/test_user_preferences.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py"
            ],
            [
                "tests/test_spend/test_spend_events/test_reimbursement_triggers.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_currency_conversion_fee.py",
                "tests/test_flex/test_celery_tasks/test_notify_scary_balances.py",
                "tests/test_approval_policy/api/test_apply_bill_actions.py",
                "tests/test_billing/test_products/test_saas.py",
                "tests/test_magic_link/test_bill_pay_magic_links.py",
                "tests/test_developer/test_card_program/test_card_program_api.py",
                "tests/test_celery/test_create_vendors_then_push.py",
                "tests/test_reimbursement/test_api/test_schemas.py",
                "tests/test_travel/test_trips/test_trips.py",
                "tests/test_billing/test_public_api/test_subscriptions.py",
                "tests/test_receipt/test_text_based_match/test_merchant_domain_match.py",
                "tests/test_event_history/test_card_request_api.py",
                "tests/test_flex/test_services/test_is_flex_eligible_for_partial_payment.py",
                "tests/test_flex/test_public_api/test_offer_unlinked_entity.py",
                "tests/test_invite/test_dao/test_invite_revocation.py",
                "tests/test_financing_application/test_utils.py",
                "tests/test_checklist/test_checkers/test_checker_can_give_requested_limit.py",
                "tests/test_spend_allocations/test_api/test_spend_allocation_request.py",
                "tests/test_vendor_network/test_api/test_bank_api.py",
                "tests/test_transaction/test_api/test_get_recurring_memo_metadata.py",
                "tests/test_statement/test_models/test_adjustments.py",
                "tests/test_growth_intelligence/test_services.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_interpret/test_interpret.py",
                "tests/test_webhooks/test_email_dao.py",
                "tests/test_banking/test_api/test_get_manual_bank_statement_metadata.py",
                "tests/test_banking/test_models.py",
                "tests/test_vendor_network/test_api/test_address_api.py",
                "tests/test_delinquency/test_tasks.py",
                "tests/test_utils/test_group_pagination.py",
                "tests/test_communication/test_api/test_slack_app_home_tab.py",
                "tests/test_okta_scim/test_dao.py",
                "tests/test_accounting/test_providers/test_netsuite_rest/test_types.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_accounting/test_clients/test_xero.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_celery/test_communicate/test_authorizer_declined.py",
                "tests/test_savings/test_api/test_savings_admin_api.py",
                "tests/test_accounting/test_api/test_provider_csv_download.py",
                "tests/test_billing/test_admin_api/test_statement_payment.py",
                "tests/test_financing_application/test_api/test_kyc.py",
                "tests/test_accounting/test_suggested_rules/test_public_api.py",
                "tests/test_reimbursement/test_api/test_reimbursement_accounting_rules.py",
                "tests/test_customer_management/test_models.py",
                "tests/test_celery/test_banking/test_manual_upgrade_tasks.py",
                "tests/test_developer/test_location/test_location_api.py",
                "tests/test_receipt/test_api/test_upload_receipt.py",
                "tests/test_business/test_entity/test_entity_migration.py",
                "tests/test_business/test_api/test_admin_oauth_export_import.py",
                "tests/test_flex/test_services/test_risk_holds.py",
                "tests/test_profile/test_dao/test_delete_user.py",
                "tests/helpers/test_helpers.py",
                "tests/test_celery/test_banking/test_handle_ach_duplicates_for_bank_account.py",
                "tests/test_profile/test_api/test_admin_change_user.py",
                "tests/test_card_switching/test_card_switching_communication.py",
                "tests/test_transaction/test_schemas.py",
                "tests/test_webhooks/test_travel_receipt.py",
                "tests/test_profile/test_mfa_types.py",
                "tests/test_flex/test_services/test_flex_pricing.py",
                "tests/test_authentication/test_dao.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_interpret/test_interpret.py",
                "tests/test_webhooks/test_email_dao.py",
                "tests/test_banking/test_api/test_list_institutions.py",
                "tests/test_banking/test_api/test_upload_manual_bank_statement.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_gmail_integration_opportunity.py",
                "tests/test_communication/test_api/test_slack_preference_override.py",
                "tests/test_communication_platform/test_clients/test_push_notification_client.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_bill_pay_opportunity.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_checklist/test_evaluate_checklist.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_spend_request/test_public_api.py",
                "tests/test_banking/test_api/test_debit_check.py",
                "tests/test_profile/test_api/test_ramp_fully_authenticate.py",
                "tests/test_fraud/test_card_transaction_fraud_alerts.py",
                "tests/test_bill_pay/test_api/test_list_bill_templates.py",
                "tests/test_billing/test_public_api/test_statements.py",
                "tests/test_card/test_services/test_bulk_programs.py",
                "tests/test_flex/test_public_api/test_flex_recommendations.py",
                "tests/test_metrics/test_accounting_lists_metrics.py",
                "tests/test_accounting/test_lists/test_apis/test_category_csv_upload.py",
                "tests/test_celery/risk_automation/test_regular_tasks.py",
                "tests/test_profile/test_api/test_copilot_crud.py",
                "tests/test_transaction/test_query/test_transaction_interactions.py",
                "tests/test_transaction/test_services/test_dispute_refunds.py",
                "tests/test_transaction/factories/test_factories.py",
                "tests/test_transaction/test_api/test_manual_override_api.py",
                "tests/test_celery/test_communicate/test_hris.py",
                "tests/test_fraud/test_reimbursement_fraud_rules.py",
                "tests/test_banking/test_api/test_admin_api_unlock_limit.py",
                "tests/test_accounting/test_lists/test_apis/test_list_tracking_category_options.py",
                "tests/test_receipt_integrations/test_travelperk/test_public_api.py",
                "tests/test_flex/test_public_api/test_flex_settings.py",
                "tests/test_customer/test_spacex.py",
                "tests/test_banking/test_utils.py",
                "tests/test_internal_tooling/test_services.py",
                "tests/test_reimbursement/test_schema.py",
                "tests/test_webhooks/marqeta/test_mixins/test_digitalwallettokentransition_webhooks.py",
                "tests/test_utils/test_sessions.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_outlook_integration_opportunity.py",
                "tests/test_stripe/test_db_routines/test_new_stripe_transaction.py",
                "tests/test_utils/test_group_pagination.py",
                "tests/test_communication/test_api/test_slack_app_home_tab.py",
                "tests/test_okta_scim/test_dao.py",
                "tests/test_accounting/test_providers/test_netsuite_rest/test_types.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_accounting/test_clients/test_xero.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_docs/test_restx.py"
            ],
            [
                "tests/test_celery/test_spend_allocations_backfill.py",
                "tests/test_accounting/test_lists/test_apis/test_list_suggested_tracking_category_options.py",
                "tests/test_celery/test_communicate/test_communicate_transaction.py",
                "tests/test_billing/test_celery_tasks/test_update_statement_payment_status.py",
                "tests/test_celery/test_banking/test_bank_statements/test_finicity_bank_statement_tasks.py",
                "tests/test_banking/test_dedupe_ach_match_accounts.py",
                "tests/test_flex/test_celery_tasks/test_installment_payment_collection_notice.py",
                "tests/test_spend_allocations/test_dao/test_spend_allocation_visibility.py",
                "tests/test_celery/test_banking/test_bank_statements/test_teller_bank_statement_tasks.py",
                "tests/test_price_intelligence/test_public_api.py",
                "tests/test_hris/test_hris_task.py",
                "tests/test_ecommerce/test_tasks/test_delete_rutter_connection.py",
                "tests/test_fraud/test_services.py",
                "tests/test_spend_allocations/test_services/test_accounting_migration.py",
                "tests/test_flex/test_celery_tasks/test_post_origination_principal_sweep.py",
                "tests/test_accounting/test_unshow.py",
                "tests/test_celery/test_business_tasks.py",
                "tests/test_magic_link/test_vendor_upload_payment_details.py",
                "tests/test_profile/test_api/test_set_date_of_birth.py",
                "tests/test_spend_allocations/test_services/test_reissue_card.py",
                "tests/test_checklist/test_checkers/test_checker_below_max_automateable_limit.py",
                "tests/test_external_firm/routes/admin_api/test_migrations_api.py",
                "tests/test_webhooks/test_scale.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_webhooks/test_rossum.py",
                "tests/test_profile/test_dao/test_get_business_managers.py",
                "tests/test_business/test_api/test_auth_total_resource_count.py",
                "tests/test_celery/test_fraud/test_log_ofac_checks.py",
                "tests/test_customer_management/test_schema.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_qbr/test_opportunities/test_compliance_opportunities/test_submission_policy_opportunity.py",
                "tests/test_billing/test_services/test_decorators.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_bill_pay_opportunity.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_checklist/test_evaluate_checklist.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_accounting/test_mapping/test_services.py",
                "tests/test_reimbursement/test_payment_service.py",
                "tests/test_metrics/test_spend/test_service.py",
                "tests/test_transaction/test_services/test_dispute_processor.py",
                "tests/test_transaction/test_api/test_transaction_transitions/test_create_transitions.py",
                "tests/test_flex/test_celery_tasks/test_cmp_callbacks.py",
                "tests/test_approval_policy/test_tasks.py",
                "tests/test_flex/test_celery_tasks/test_risk_holds.py",
                "tests/test_communication/test_admin_communication/test_daily_digest/test_daily_digest.py",
                "tests/test_payments/test_external/test_services/test_debit_checks.py",
                "tests/test_card/test_services/test_services.py",
                "tests/test_card/test_api/test_marqeta_functions.py",
                "tests/test_card/test_validation/test_card_validation.py",
                "tests/test_stale_gla/test_api/test_public_api.py",
                "tests/test_external_firm/_internal/services/test_proposals.py",
                "tests/test_developer/test_cashback/test_cashback_api.py",
                "tests/test_fraud/test_transaction/test_confirm_transaction_is_fraud.py",
                "tests/test_flex/test_celery_tasks/test_offer_acceptance.py",
                "tests/test_checklist/test_checkers/test_checker_all_manual_bank_statements_parsed_by_inscribe.py",
                "tests/test_banking/test_api/test_admin_api_bank_account_test_routes.py",
                "tests/test_ledger/test_clients/test_fragment.py",
                "tests/test_accounting/test_coding_v2/test_services.py",
                "tests/test_accounting/test_validation/test_dao.py",
                "tests/test_webhooks/marqeta/test_api/test_tokenization.py",
                "tests/test_ledger/test_internal/test_dao/test_balances.py",
                "tests/test_communication/test_schemas.py",
                "tests/test_external_firm/test_external_firm_invite_model.py",
                "tests/test_communication/test_api/test_slack_channel_list.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_gmail_integration_opportunity.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_celery/test_communicate/test_communicate_to_admin_email_integration_enabled.py",
                "tests/test_external_firm/communication/test_communicate_external_firm_authorization_revoked_by_spend_user.py",
                "tests/test_async_job/test_routes.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_checklist/test_evaluate_checklist.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_payments/test_services/test_engine.py",
                "tests/test_customer_management/test_dao.py",
                "tests/test_reimbursement/test_state_machine.py",
                "tests/test_developer/test_transaction/test_transaction_api.py",
                "tests/test_transaction/test_api/test_batch_transaction_update.py",
                "tests/test_accounting/test_lists/test_apis/test_list_active_categories.py",
                "tests/test_proxies/authorizer/test_authorizer_spend_intervals.py",
                "tests/test_spend_allocations/test_api/test_admin_api.py",
                "tests/test_business/test_api/test_admin_delete_accounting_data.py",
                "tests/test_accounting/test_providers/test_xero/test_client.py",
                "tests/test_celery/test_statement.py",
                "tests/test_billing/test_services/test_seats.py",
                "tests/test_invoices/test_dao.py",
                "tests/test_transaction/test_utils.py",
                "tests/test_flex/test_services/test_lock_in_flex_for_bill.py",
                "tests/test_demo/test_external_firm_demo_generation.py",
                "tests/test_operations/test_api/test_document_request.py",
                "tests/test_profile/test_api/test_existing_business.py",
                "tests/test_data_export_async_job/test_api.py",
                "tests/test_external_firm/routes/admin_api/test_admin_api.py",
                "tests/test_flex/test_statements/test_html_formatter.py",
                "tests/test_external_firm/routes/admin_api/test_migrations_api.py",
                "tests/test_webhooks/test_scale.py",
                "tests/test_webhooks/test_invoice_email_webhook.py",
                "tests/test_webhooks/test_rossum.py",
                "tests/test_transaction/test_dao/test_is_transaction_freshly_authorized.py",
                "tests/test_business/test_api/test_auth_total_resource_count.py",
                "tests/test_celery/test_fraud/test_log_ofac_checks.py",
                "tests/test_customer_management/test_schema.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_qbr/test_opportunities/test_compliance_opportunities/test_submission_policy_opportunity.py",
                "tests/test_billing/test_services/test_decorators.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_bill_pay_opportunity.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_checklist/test_evaluate_checklist.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_bill_pay/test_dao.py",
                "tests/test_spend_allocations/test_dao/test_paginated_spend_allocation.py",
                "tests/test_metrics/test_spend/test_public_api.py",
                "tests/test_transaction/test_dao/test_auto_mark_ready_card_rules.py",
                "tests/test_bill_pay/test_vendor_credits/test_vendor_credits_api.py",
                "tests/test_savings/test_api/test_savings_public_api.py",
                "tests/test_communication/test_utils.py",
                "tests/test_card/test_api/test_admin_card_reissuance.py",
                "tests/test_invite/test_api/test_validate_invite.py",
                "tests/test_referral/tasks/test_referral_celery_tasks.py",
                "tests/test_card_programs/test_utils/test_create_card.py",
                "tests/test_transaction/test_api/test_policy_exemption.py",
                "tests/test_issuing/test_services/test_create_cardholder.py",
                "tests/test_flex/test_admin_api/test_remove_flex_from_bill.py",
                "tests/test_metrics/test_spend/test_utils.py",
                "tests/test_communication/test_user_communication/test_missing_items_needed.py",
                "tests/test_spend_allocations/test_services/test_approval_services.py",
                "tests/test_flex/test_dao/test_flex.py",
                "tests/test_accounting/test_api/test_auto_fill.py",
                "tests/test_profile/test_dao/test_bulk_queries.py",
                "tests/test_stripe_app/test_user_api/test_link_user.py",
                "tests/test_accounting/test_lists/test_models.py",
                "tests/test_proxies/authorizer/test_authorizer.py",
                "tests/test_event_history/test_user_api.py",
                "tests/test_transaction/test_services/test_dispute_evidence.py",
                "tests/test_celery/test_send_submitter_daily_rejected_reimbursements.py",
                "tests/test_backfills/instances/test_backfill_won_mq_merchant_disputes_20230621175158.py",
                "tests/test_celery/test_fraud/test_log_ofac_checks.py",
                "tests/test_risk_accounts/test_schemas.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_communication_platform/test_clients/test_push_notification_client.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_webhooks/marqeta/test_replay_marqeta_event.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_checklist/test_evaluate_checklist.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_celery/risk_automation/test_auto_approval.py",
                "tests/test_flex/test_public_api/test_single_bill_offer.py",
                "tests/test_accounting/test_attribution/test_rules_v2.py",
                "tests/test_developer/test_accounting/test_accounting_api.py",
                "tests/test_merchant/test_api/test_merchant_detail.py",
                "tests/test_transaction_interactions/test_state_machines/test_dispute_interaction_state_machine.py",
                "tests/test_bill_pay/test_tasks/test_scheduler.py",
                "tests/test_invite/test_api/test_resend_invite.py",
                "tests/test_accounting/test_api/test_accounting_admin_api.py",
                "tests/test_merchant/test_dao/test_assign_or_update.py",
                "tests/test_flex/test_celery_tasks/test_flex_fee_daily_log.py",
                "tests/test_receipt/test_verify_receipt.py",
                "tests/test_communication/test_slack_communication/test_decline_spend_allocation_request.py",
                "tests/test_referral/tasks/test_payouts.py",
                "tests/test_flex/test_services/test_generate_and_retrieve_legal_agreement_s3.py",
                "tests/test_receipt/test_api/test_public_api.py",
                "tests/test_magic_link/test_services.py",
                "tests/test_card_switching/test_services/test_initialize_sunlight.py",
                "tests/test_card_switching/test_card_switching_communication.py",
                "tests/test_payee/test_models/test_core.py",
                "tests/test_configuration/test_api.py",
                "tests/test_profile/test_dao/test_identity_linked_users.py",
                "tests/test_flex/test_services/test_flex_pricing.py",
                "tests/test_flex/test_admin_api/test_fee_components.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_interpret/test_interpret.py",
                "tests/test_webhooks/test_email_dao.py",
                "tests/test_banking/test_api/test_list_institutions.py",
                "tests/test_banking/test_api/test_upload_manual_bank_statement.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_gmail_integration_opportunity.py",
                "tests/test_communication/test_api/test_slack_preference_override.py",
                "tests/test_communication_platform/test_clients/test_push_notification_client.py",
                "tests/test_utils/test_pagination.py",
                "tests/test_webhooks/marqeta/test_replay_marqeta_event.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_external_firm/tasks/test_on_firm_initiated_referral_created.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_celery/test_policy_tasks.py",
                "tests/test_savings/test_monthly_spend_report/test_monthly_spend_report.py",
                "tests/test_payments/test_services/test_ledger/test_entries.py",
                "tests/test_fixtures/test_load_test/test_tracking_categories.py",
                "tests/test_in_app_onboarding/test_services.py",
                "tests/test_flex/test_public_api/test_list_flex.py",
                "tests/test_accounting/test_api/test_accounting_date_override.py",
                "tests/test_spend_allocations/test_dao/test_renaming_dao.py",
                "tests/test_customer/test_api/test_client.py",
                "tests/test_payments/test_clients/test_kyc_fetcher.py",
                "tests/test_flex/test_admin_api/test_dq_balance.py",
                "tests/test_flex/test_celery_tasks/test_post_daily_summary.py",
                "tests/test_flex/test_celery_tasks/test_check_balance_sheet_utilization.py",
                "tests/test_accounting/test_csv_generator.py",
                "tests/test_accounting/test_command_center/test_dao.py",
                "tests/test_external_firm/routes/public_api/test_public_firm_proposal_routes.py",
                "tests/test_accounting/test_coding_v2/test_utils.py",
                "tests/test_authentication/test_api/test_app_attest.py",
                "tests/test_checklist/test_checkers/test_checker_no_unresolved_exceptions.py",
                "tests/test_accounting/test_sync/test_sync_transfer.py",
                "tests/test_configuration/test_api.py",
                "tests/test_fixtures/test_load_test/test_users.py",
                "tests/test_stripe/test_card_transitions.py",
                "tests/test_checklist/test_checkers/test_checker_accounting_data_verified.py",
                "tests/test_webhooks/test_comply_advantage.py",
                "tests/test_profile/test_api/test_session_revocation_and_signout.py",
                "tests/test_flex/test_dao/test_onboarding.py",
                "tests/test_communication_platform/test_clients/test_email_client.py",
                "tests/test_fraud/test_admin_api/test_whitelist_card_for_3ds.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_celery/test_banking/test_manual_transaction_tasks.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_profile/test_api/test_user_preferences.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_stripe/test_stripe_utils.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_reimbursement/test_dao.py",
                "tests/test_reimbursement/test_api/test_reimbursement_approval_chain.py",
                "tests/test_vendor_network/test_api/test_invite_api.py",
                "tests/test_billing/test_services/test_statement.py",
                "tests/test_transaction/test_api/test_transaction_approval_chains.py",
                "tests/test_hris/test_merge.py",
                "tests/test_card/test_api/test_export_cards.py",
                "tests/test_invite/test_api/test_delete_invite.py",
                "tests/test_manager/test_dao.py",
                "tests/test_flex/test_services/test_unlink_flex_offers.py",
                "tests/test_webhooks/test_card_activation.py",
                "tests/test_business/test_api/test_opt_in_features.py",
                "tests/test_flex/test_services/test_flex_business_eligibility_validator.py",
                "tests/test_billing/test_admin_api/test_custom_pricing.py",
                "tests/test_transaction/test_dao/test_filter_transaction_ids_by_business_id.py",
                "tests/test_flex/test_public_api/test_onboarding.py",
                "tests/test_switching/test_dao.py",
                "tests/test_receipt_integrations/test_api/test_public_api.py",
                "tests/test_card/test_dao/test_cyclic_card_limit_query.py",
                "tests/test_balance/test_dao.py",
                "tests/test_external_firm/test_external_firm_to_business_authorization_proposal_model.py",
                "tests/test_transaction/test_dao/test_suspicious_transactions.py",
                "tests/test_payments/test_services/test_risk.py",
                "tests/test_checklist/test_checkers/test_checker_accounting_data_verified.py",
                "tests/test_card/test_dao/test_cards_for_identity.py",
                "tests/test_customer_management/test_utils.py",
                "tests/test_ocr/test_internal/test_services.py",
                "tests/test_profile/test_create_user/test_create_business_owner.py",
                "tests/test_fraud/test_admin_api/test_whitelist_card_for_3ds.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_celery/test_banking/test_manual_transaction_tasks.py",
                "tests/test_celery/test_communicate/test_communicate_to_admin_email_integration_enabled.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_spend/test_admin_api.py",
                "tests/test_profile/test_api/test_user_change_email.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_accounting/test_providers/test_sage/test_provider_context.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_payments/test_services/test_init.py",
                "tests/test_celery/test_transfer_tasks.py",
                "tests/test_celery/test_communicate/test_send_statement_upload_reminder_email.py",
                "tests/test_communication/test_slack_communication/test_new_reimbursement_request.py",
                "tests/test_flex/test_clients/test_bill_pay/test_public_api.py",
                "tests/test_card/test_api/test_ship_physical_cards.py",
                "tests/test_financing_application/test_api/test_application.py",
                "tests/test_loan_origination/test_celery_tasks/test_loan_balance_monthly.py",
                "tests/test_internal_tooling/test_operational_definitions/test_admin_api.py",
                "tests/test_stripe_app/test_merchants/test_get_merchants.py",
                "tests/test_spend/test_spend_events/test_dao/test_dao.py",
                "tests/test_approval_policy/services/test_replacing_user_in_approval_chains.py",
                "tests/test_merchant/test_api/test_vendor_contracts.py",
                "tests/test_vendor_network/test_api/test_admin_invites_vendor_user.py",
                "tests/test_card/test_api/test_card_policy_enforcement.py",
                "tests/test_approval_policy/services/test_create_assigned_entities_for_step.py",
                "tests/test_banking/test_linking/test_providers/test_finicity/test_transactions.py",
                "tests/test_transaction_interactions/test_state_machines/test_transaction_interaction_shared_state_machine.py",
                "tests/test_metrics/test_users/test_public_api.py",
                "tests/test_flex/test_admin_api/test_business_pricing_plan_eligibility.py",
                "tests/test_celery/test_payee/test_document_tasks.py",
                "tests/test_profile/test_api/test_request_forgot_password.py",
                "tests/test_payments/test_services/test_risk.py",
                "tests/test_webhooks/test_reimbursement_email_webhooks.py",
                "tests/test_banking/test_utils.py",
                "tests/test_ledger/test_internal/test_dao/test_balances.py",
                "tests/test_qbr/test_opportunities/test_compliance_opportunities/test_travel_policy_opportunity.py",
                "tests/test_profile/test_create_user/test_create_business_owner.py",
                "tests/test_in_app_onboarding/test_public_api.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_celery/test_banking/test_manual_transaction_tasks.py",
                "tests/test_celery/test_communicate/test_communicate_to_admin_email_integration_enabled.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_spend/test_admin_api.py",
                "tests/test_profile/test_api/test_user_preferences.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_accounting/test_providers/test_sage/test_provider_context.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_accounting/test_sync/test_sync_reimbursement.py",
                "tests/test_savings/test_insight_types/test_generate_potential_insights.py",
                "tests/test_accounting/test_coding_v2/test_dao.py",
                "tests/test_transaction/test_api/test_transaction_transitions/test_bypass_transitions.py",
                "tests/test_business/test_api/test_admin_business_summary.py",
                "tests/test_fraud/test_bin_attack_suppression.py",
                "tests/test_accounting/test_api/test_accounting_date_override.py",
                "tests/test_bill_pay/test_services/test_accounting.py",
                "tests/test_mailbox/test_api/test_public_api.py",
                "tests/test_profile/test_dao/test_user_custom_field_approvers.py",
                "tests/test_flex/test_dao/test_flex_installments_eligible_for_collection.py",
                "tests/test_manager/test_api/test_view_transactions.py",
                "tests/test_travel/test_celery/test_communication.py",
                "tests/test_billing/test_admin_api/test_custom_pricing.py",
                "tests/test_ledger/test_internal/test_services/test_provider.py",
                "tests/test_banking/test_heron_integration/test_heron_services.py",
                "tests/test_transaction/test_services/test_dispute_utils.py",
                "tests/test_receipt_integrations/test_api/test_public_api.py",
                "tests/test_business/test_api/test_admin_business_reset.py",
                "tests/test_flex/test_public_api/test_estimated_fees_for_business.py",
                "tests/test_external_firm/test_external_firm_to_business_authorization_proposal_model.py",
                "tests/test_internal_tooling/test_dao.py",
                "tests/test_payments/test_services/test_risk.py",
                "tests/test_flex/test_public_api/test_risk_holds.py",
                "tests/test_card/test_dao/test_cards_for_identity.py",
                "tests/test_accounting/test_platform/test_dao.py",
                "tests/test_ocr/test_internal/test_services.py",
                "tests/test_profile/test_create_user/test_create_business_owner.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_submitted_reimbursement_opportunity.py",
                "tests/test_business/test_api/test_blacklist_transfer_checks_businesses.py",
                "tests/test_celery/test_banking/test_manual_transaction_tasks.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_amazon_integration_opportunity.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_spend/test_admin_api.py",
                "tests/test_profile/test_api/test_user_change_email.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_accounting/test_providers/test_sage/test_provider_context.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_celery/test_accounting_sync.py",
                "tests/test_accounting/test_mapping/test_dao.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_currency_conversion_fee.py",
                "tests/test_communication/test_slack_communication/test_slack_user_lookup.py",
                "tests/test_invite/test_tasks/test_invite_task.py",
                "tests/test_transaction_interactions/test_services/test_dispute_interaction_service.py",
                "tests/test_merchant/test_api/test_merchant_override.py",
                "tests/test_celery/test_banking/test_heron/test_queue_new_manual_transactions_for_heron.py",
                "tests/test_transaction/test_dao/test_transaction_snapshot.py",
                "tests/test_accounting/test_sync/test_sync_invoice.py",
                "tests/test_search/test_services.py",
                "tests/test_profile/test_api/test_stripe_acceptance.py",
                "tests/test_accounting/test_clients/test_netsuite/test_netsuite_rest.py",
                "tests/test_flex/test_services/test_get_flex_entities_eligibility.py",
                "tests/test_payments/test_services/test_providers/test_complyadvantage.py",
                "tests/test_switching/test_task.py",
                "tests/test_invite/test_dao/test_invite_revocation.py",
                "tests/test_flex/test_services/test_flex_fa_eligibility_validator.py",
                "tests/test_spend/test_spend_events/test_dao/test_attendee_split.py",
                "tests/test_profile/test_api/test_receipt_upload_email_address.py",
                "tests/test_utils/test_file_utils.py",
                "tests/test_issuing/test_services/test_create_card.py",
                "tests/test_invite/test_api/test_admin_invite_revocation.py",
                "tests/test_authentication/test_api/test_admin_api.py",
                "tests/test_webhooks/marqeta/test_api/test_tokenization.py",
                "tests/test_profile/test_dao/test_permissions.py",
                "tests/test_loan_origination/test_dao/test_loan_payment.py",
                "tests/test_external_firm/test_external_firm_invite_model.py",
                "tests/test_business/test_api/test_location_owners.py",
                "tests/test_risk_accounts/test_schemas.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_communication_platform/test_clients/test_push_notification_client.py",
                "tests/test_profile/test_dao/test_receipt_forwarding_emails.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_accounting/test_providers/test_netsuite_rest/test_types.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_external_firm/tasks/test_on_firm_initiated_referral_created.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_approval_policy/services/test_services.py",
                "tests/test_fixtures/test_load_test/test_cards.py",
                "tests/test_celery/test_communicate/test_communicate_receipt.py",
                "tests/test_merchant/test_api/test_merchant_admin_api.py",
                "tests/test_alerts/test_public_api.py",
                "tests/test_spend/test_services.py",
                "tests/test_accounting/test_lists/test_dao.py",
                "tests/test_banking/test_linking/test_daos/test_finicity/test_get_useful_connections.py",
                "tests/test_webhooks/stripe/test_stripe_events.py",
                "tests/test_profile/test_api/test_upload_id_docs.py",
                "tests/test_flex/test_celery_tasks/test_message_outstanding_dqs.py",
                "tests/test_vendor_network/test_api/test_onboarding_api.py",
                "tests/test_payments/test_external/test_services/test_rails/test_checks.py",
                "tests/test_external_firm/test_external_firm_authorization_proposal_model.py",
                "tests/test_flex/test_dao/test_installments.py",
                "tests/test_capital_markets/test_utils.py",
                "tests/test_receipt_integrations/test_amazon/test_admin_api.py",
                "tests/test_magic_link/test_services.py",
                "tests/test_card/test_api/test_card_category_and_vendor_copy.py",
                "tests/test_banking/test_api/test_user_bank_account.py",
                "tests/test_celery/test_transaction.py",
                "tests/test_fixtures/test_load_test/test_reimbursements.py",
                "tests/test_flex/test_services/test_unlinked_entity_eligibility.py",
                "tests/test_banking/test_api/test_set_as_default.py",
                "tests/test_hris/test_invite.py",
                "tests/test_external_firm/tasks/reminder/test_daily_reminder_pending_external_firm_application.py",
                "tests/test_business/test_api/test_admin_update_business_limit.py",
                "tests/test_profile/test_api/test_existing_identity.py",
                "tests/test_profile/test_create_user/test_create_invited_user.py",
                "tests/test_merchant/test_dao/test_delete_all_but_most_recent_predictions_for_business.py",
                "tests/test_stripe/test_db_routines/test_new_stripe_transaction.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_billing/test_services/test_create_active_or_trial_subscription.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_banking/test_api/test_update_manual_bank_connections.py",
                "tests/test_qbr/services/test_is_business_eligible_for_qbr.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_celery/test_reimbursement_tasks.py",
                "tests/test_payments/test_services/test_compliance.py",
                "tests/test_financing_application/test_api/test_exception.py",
                "tests/test_transaction/test_api/test_disputes.py",
                "tests/test_feature_flags/test_admin_api.py",
                "tests/test_developer/test_bill/test_bill_api.py",
                "tests/test_billing/test_services/test_billing_statement_payment.py",
                "tests/test_card/test_api/test_card_edit_to_existing_card.py",
                "tests/test_transaction_interactions/test_state_machines/test_submission_policy_interaction_state_machine.py",
                "tests/test_payments/test_clients/test_wise_onboarding.py",
                "tests/test_accounting/test_coding_v2/test_split_reimbursements.py",
                "tests/test_flex/test_public_api/test_get_legal_agreement_s3_uri.py",
                "tests/test_flex/test_services/test_move_state_of_flex_forward.py",
                "tests/test_card/test_factories.py",
                "tests/test_transaction/test_dao/test_add_transaction/test_add_transaction_canada.py",
                "tests/test_accounting/test_attribution/test_resolve_subsidiary/test_provider_option_for_subsidiary.py",
                "tests/test_accounting/test_sync/test_get_reimbursement_id_to_accounting_coding.py",
                "tests/test_flex/test_services/test_flex_fa_eligibility_validator.py",
                "tests/test_checklist/test_checkers/test_checker_can_give_requested_limit.py",
                "tests/test_flex/test_celery_tasks/test_communicate_flex_created.py",
                "tests/test_transaction/test_schemas.py",
                "tests/test_business/test_api/test_admin_bulk_change_department_location.py",
                "tests/test_ecommerce/test_api/test_public_api.py",
                "tests/test_restrictions/test_utils.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_transaction/test_model/test_models.py",
                "tests/test_banking/test_api/test_business_bank_account_queue.py",
                "tests/test_business/test_api/test_auth_total_resource_count.py",
                "tests/test_celery/test_fraud/test_log_ofac_checks.py",
                "tests/test_customer_management/test_schema.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_hris/test_models.py",
                "tests/test_async_job/test_routes.py",
                "tests/test_receipt/test_parse_email_receipts.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_spend/test_spend_criteria/test_services.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py"
            ],
            [
                "tests/test_flex/test_services/test_installments.py",
                "tests/test_approval_policy/api/test_apply_reimbursement_actions.py",
                "tests/test_accounting/test_sync/test_apis.py",
                "tests/test_celery/test_unknown_tasks.py",
                "tests/test_communication/test_api/test_slack_spend_allocation_request.py",
                "tests/test_merchant/test_recurrence_score_score.py",
                "tests/test_accounting/test_sync/test_auto_fill.py",
                "tests/test_billing/test_services/test_notifications.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_interpret/test_chargebacks.py",
                "tests/test_accounting/test_attribution/test_resolve_subsidiary/test_transaction_resolved_subsidiary.py",
                "tests/test_flex/test_celery_tasks/test_business_daily_summary.py",
                "tests/test_banking/test_api/test_bank_account_schema/test_bank_account_ownership_status.py",
                "tests/test_card/test_dao/test_card_requests_with_approval_chains.py",
                "tests/test_spend_request/test_backfill.py",
                "tests/test_billing/test_services/test_post_billing_transaction.py",
                "tests/test_rewards/test_api/test_redeem.py",
                "tests/test_transaction/test_api/test_manual_override_api.py",
                "tests/test_checklist/test_checkers/test_checker_industry_taxonomy_is_correct.py",
                "tests/test_qbr/public_api/test_opportunities_resource.py",
                "tests/test_hris/test_services.py",
                "tests/test_profile/test_api/test_user_sign_up_status_check.py",
                "tests/test_celery/test_communicate/test_communicate_invitation_to_join_team.py",
                "tests/test_flex/test_admin_api/test_get_business_status.py",
                "tests/test_flex/test_dao/test_onboarding_logs.py",
                "tests/test_flex/test_admin_api/test_fee_components.py",
                "tests/test_billing/test_celery_tasks/test_cycle_statements.py",
                "tests/test_accounting/test_api/test_refresh_tracking_categories.py",
                "tests/test_banking/test_api/test_admin_api_financial_accounts.py",
                "tests/test_banking/test_models.py",
                "tests/test_demo/test_create_fixture_business.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_communication/test_api/test_send_mass_email.py",
                "tests/test_profile/test_utils/test_scope_lifetime_helpers.py",
                "tests/test_webhooks/marqeta/test_replay_marqeta_event.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_external_firm/tasks/test_on_firm_initiated_referral_created.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_accounting/test_sync/test_sync_transaction.py",
                "tests/test_bill_pay/test_vendor_credits/test_vendor_credits.py",
                "tests/test_flex/test_integration/test_payment_failures.py",
                "tests/test_flex/test_services/test_assign_offer_terms.py",
                "tests/test_webhooks/marqeta/test_api/test_marqeta_events_api.py",
                "tests/test_flex/test_celery_tasks/test_send_risk_ops_upcoming_ineligibility.py",
                "tests/test_loan_origination/test_celery_tasks/test_loan_balance_daily.py",
                "tests/test_billing/test_services/test_notifications.py",
                "tests/test_transaction_interactions/test_state_machines/test_submission_policy_interaction_state_machine.py",
                "tests/test_accounting/test_providers/test_quickbooks/test_client.py",
                "tests/test_card/test_api/test_card_details.py",
                "tests/test_internal_tooling/test_operational_definitions/test_business/test_dao.py",
                "tests/test_workflows/test_services/test_core.py",
                "tests/test_billing/test_admin_api/test_statement.py",
                "tests/test_transaction/test_formatters/test_csv_formatter.py",
                "tests/test_alerts/test_services.py",
                "tests/test_accounting/test_api/test_department_tracking_category_map.py",
                "tests/test_celery/test_communicate/test_hris.py",
                "tests/test_transfer/test_api/test_listing_transfers.py",
                "tests/test_accounting/test_sync/test_sync_statement_credit.py",
                "tests/test_delinquency/test_notifications.py",
                "tests/test_issuing/test_services/test_create_card.py",
                "tests/test_checklist/test_checkers/test_checker_passes_underwriting.py",
                "tests/test_webhooks/test_scale.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_celery/test_communicate/test_communicate_verify_email.py",
                "tests/test_transaction/test_dao/test_is_transaction_freshly_authorized.py",
                "tests/test_negotiations/api/test_admin_api.py",
                "tests/test_okta_scim/test_tasks.py",
                "tests/test_partner_rewards/test_dao.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_utils/test_group_pagination.py",
                "tests/test_communication/test_api/test_slack_app_home_tab.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_profile/test_api/test_user_preferences.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_accounting/test_clients/test_xero.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py"
            ],
            [
                "tests/test_payee/test_routes/test_public_api.py",
                "tests/test_customer_management/test_services.py",
                "tests/test_communication/test_slack_communication/test_add_memo_to_receipt_modal.py",
                "tests/test_proxies/authorizer/test_services.py",
                "tests/test_event_history/test_transaction_api.py",
                "tests/test_celery/test_bill_pay/test_risk_tasks.py",
                "tests/test_flex/test_models.py",
                "tests/test_qbr/test_report/test_operational_efficiency/test_accounting_rules_metric.py",
                "tests/test_rules/test_api/test_public_endpoints.py",
                "tests/test_profile/test_api/test_mfa.py",
                "tests/test_business/test_api/test_business_sso.py",
                "tests/test_accounting/test_lists/test_seek_and_destroy_duplicates.py",
                "tests/test_receipt/test_e_receipt.py",
                "tests/test_banking/test_api/test_bank_account_schema/test_bank_account_debitability_status.py",
                "tests/test_flex/test_celery_tasks/test_repayment_failure_risk.py",
                "tests/test_receipt/test_api/test_delete_receipt.py",
                "tests/test_loan_origination/test_celery_tasks/test_beneficial_owner_daily.py",
                "tests/test_fraud/test_transaction/test_confirm_transaction_is_fraud.py",
                "tests/test_ledger/test_services/test_entries.py",
                "tests/test_banking/test_linking/test_tasks/test_provider_tasks.py",
                "tests/test_banking/test_api/test_user_ach_debit_check.py",
                "tests/test_ledger/test_clients/test_fragment.py",
                "tests/test_external_firm/_internal/services/test_firm_users.py",
                "tests/test_flex/test_dao/test_risk_holds.py",
                "tests/test_merchant/test_dao/test_matching_merchants_by_amount_of_spend.py",
                "tests/test_ledger/test_internal/test_dao/test_balances.py",
                "tests/test_profile/test_dao/test_get_business_managers.py",
                "tests/test_approval_policy/api/test_admin_api.py",
                "tests/test_business/test_api/test_location_owners.py",
                "tests/test_demo/test_create_fixture_business.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_billing/test_admin_api/test_transaction.py",
                "tests/test_profile/test_utils/test_scope_lifetime_helpers.py",
                "tests/test_flex/test_public_api/test_installment_payment_history.py",
                "tests/test_external_firm/routes/admin_api/test_external_firm_crud.py",
                "tests/test_banking/test_api/test_bank_account_subtype_update.py",
                "tests/test_ledger/test_services/test_accounts.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_payments/test_celery/test_wise_settlement.py",
                "tests/test_communication/test_slack_communication/test_accept_card_request.py",
                "tests/test_spend/test_public_api_spend_metrics.py",
                "tests/test_transaction/test_dao/test_restrict_transaction_canonical.py",
                "tests/test_flex/test_celery_tasks/test_send_emails_for_upcoming_payments.py",
                "tests/test_workflows/test_public_api.py",
                "tests/test_rules_engine/test_rules_engine_services.py",
                "tests/test_fixtures/test_fixture_bills.py",
                "tests/test_flex/test_services/test_create_installments_from_flex.py",
                "tests/test_flex/test_celery_tasks/test_finalize_bill_financing.py",
                "tests/test_spend_allocations/test_services/test_validation_services.py",
                "tests/test_communication/test_slack_communication/test_decline_card_request.py",
                "tests/test_developer/test_dao.py",
                "tests/test_celery/test_banking/test_heron_tasks.py",
                "tests/test_backfills/instances/test_merging_duplicate_payees_20230620134139.py",
                "tests/test_receipt_integrations/test_amazon/test_celery.py",
                "tests/test_celery/test_user.py",
                "tests/test_celery/test_vendor_management_predictions.py",
                "tests/test_profile/test_api/test_invite_physical.py",
                "tests/test_approval_policy/test_utils.py",
                "tests/test_business/test_api/test_autopay_threshold.py",
                "tests/test_transaction/test_services/test_dispute_comms.py",
                "tests/test_statement/test_dao/test_statement_delinquency.py",
                "tests/test_celery/test_communicate/test_communicate_card_unlocked.py",
                "tests/test_communication_platform/test_communication_platform_tasks/test_sending.py",
                "tests/test_business/test_api/test_admin_update_business.py",
                "tests/test_reimbursement/test_schema.py",
                "tests/test_approval_policy/api/test_admin_api.py",
                "tests/test_business/test_api/test_location_owners.py",
                "tests/test_demo/test_create_fixture_business.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_billing/test_admin_api/test_transaction.py",
                "tests/test_profile/test_utils/test_scope_lifetime_helpers.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_receipt/test_parse_email_receipts.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_external_firm/tasks/test_on_firm_initiated_referral_created.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_reimbursement/test_api/test_export_reimbursements.py",
                "tests/test_bill_pay/test_api/test_list_bills.py",
                "tests/test_capital_markets/test_tasks.py",
                "tests/test_travel/test_celery/test_trips.py",
                "tests/test_accounting/test_sync/test_dao.py",
                "tests/test_flex/test_schemas.py",
                "tests/test_communication/test_api/test_slack_button_links.py",
                "tests/test_accounting/test_accounting_temporary.py",
                "tests/test_flex/test_celery_tasks/test_communicate_dq_installment_payment_reminder.py",
                "tests/test_payments/test_celery/test_fee_sweep.py",
                "tests/test_spend_request/test_schemas.py",
                "tests/test_backfills/instances/test_backfill_spend_request_permitted_spend_type_setting_id_20230626125623.py",
                "tests/test_invite/test_schemas/test_invite_schema.py",
                "tests/test_celery/test_accounting_command_center.py",
                "tests/test_backfills/instances/test_merging_duplicate_payees_20230620134139.py",
                "tests/test_business/test_api/test_create_statement.py",
                "tests/test_rules/test_services.py",
                "tests/test_magic_link/test_services.py",
                "tests/test_developer/test_spend_limit/test_celery.py",
                "tests/test_checklist/test_checkers/test_checker_no_unresolved_exceptions.py",
                "tests/test_celery/test_transaction.py",
                "tests/test_profile/test_dao/test_linked_accounts.py",
                "tests/test_ecommerce/test_api/test_public_api.py",
                "tests/test_growth_intelligence/test_services.py",
                "tests/test_celery/test_banking/test_heron/test_poll_long_processing_batch.py",
                "tests/test_profile/test_api/test_user_change_password.py",
                "tests/test_reimbursement/test_schema.py",
                "tests/test_referral/services/test_payouts_services.py",
                "tests/test_profile/test_create_user/test_create_invited_user.py",
                "tests/test_merchant/test_dao/test_delete_all_but_most_recent_predictions_for_business.py",
                "tests/test_stripe/test_db_routines/test_new_stripe_transaction.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_billing/test_services/test_create_active_or_trial_subscription.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_accounting/test_clients/test_xero.py",
                "tests/test_ledger/test_internal/test_services/test_balances.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_flex/test_clients/test_bill_pay/test_services.py",
                "tests/test_card/test_api/test_card_request.py",
                "tests/test_spend/test_public_api.py",
                "tests/test_transaction_interactions/test_state_machines/test_expense_policy_interaction_state_machine.py",
                "tests/test_reimbursement/test_api/test_admin_api.py",
                "tests/test_metrics/test_reimbursement_metrics/test_reimbursement_metrics.py",
                "tests/test_accounting/test_lists/test_refresh_tracking_categories.py",
                "tests/test_accounting/test_sync_transaction.py",
                "tests/test_event_history/test_spend_allocation_api.py",
                "tests/test_celery/test_banking/test_bank_statements/test_teller_bank_statement_tasks.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_refresh_transaction_canonical.py",
                "tests/test_hris/test_hris_task.py",
                "tests/test_statement/test_api/test_retrieve_statement.py",
                "tests/test_bill_pay/test_bill_payments.py",
                "tests/test_customer/test_api/test_transactions.py",
                "tests/test_payments/test_services/test_quotes.py",
                "tests/test_developer/test_token/test_token_api.py",
                "tests/test_flex/test_celery_tasks/test_too_many_scheduled_flexs.py",
                "tests/test_celery/test_risk.py",
                "tests/test_comments/test_public_api.py",
                "tests/test_flex/test_statements/test_pdf_formatter.py",
                "tests/test_issuing/test_services/test_create_card.py",
                "tests/test_card/test_api/test_suspend.py",
                "tests/test_flex/test_dao/test_risk_holds.py",
                "tests/test_event_history/test_user_api.py",
                "tests/test_profile/test_dao/test_permissions.py",
                "tests/test_spend_allocations/test_services/test_overrides.py",
                "tests/test_approval_policy/api/test_admin_api.py",
                "tests/test_business/test_api/test_location_owners.py",
                "tests/test_demo/test_create_fixture_business.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_hris_opportunity.py",
                "tests/test_profile/test_api/test_user_all_permissions.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_receipt/test_parse_email_receipts.py",
                "tests/test_flex/test_public_api/test_get_state_amount.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_flex/test_services/test_flex_balance_eligibility_validator.py",
                "tests/test_payments/test_celery/test_core_tasks.py",
                "tests/test_transaction/test_api/test_transaction_interactions.py",
                "tests/test_approval_policy/services/test_add_user_to_chain.py",
                "tests/test_accounting/test_api/test_providers.py",
                "tests/test_spend_allocations/test_services/test_renaming_services.py",
                "tests/test_flex/test_admin_api/test_update_loan_terms.py",
                "tests/test_bill_pay/test_bill_matching.py",
                "tests/test_flex/test_admin_api/test_installment_payment_retry.py",
                "tests/test_banking/test_services.py",
                "tests/test_approval_policy/services/test_remove_self_approvals_from_chain.py",
                "tests/test_bill_pay/test_utils.py",
                "tests/test_profile/test_api/test_linked_account_migration_flow.py",
                "tests/test_transfer/test_api/test_debit_check_status.py",
                "tests/test_transfer/test_api/test_list_transfers_admin.py",
                "tests/test_card/test_utils/test_update_card_owner.py",
                "tests/test_payments/test_clients/test_jpm.py",
                "tests/test_card/test_dao/test_update_last_card_state.py",
                "tests/test_business/test_api/test_remove_user.py",
                "tests/test_approval_policy/test_utils.py",
                "tests/test_celery/test_communicate/test_communicate_new_statement.py",
                "tests/test_transaction/test_api/test_currency_conversion.py",
                "tests/test_utils/test_locking.py",
                "tests/test_celery/financing_application/test_communicate_business_approved_if_external_firm_referral.py",
                "tests/test_transaction/test_dao/test_transaction_approval_chains.py",
                "tests/test_delinquency/test_admin_api.py",
                "tests/test_incentives/test_utils.py",
                "tests/test_bill_pay/test_services/test_accounting_schema.py",
                "tests/test_banking/test_api/test_upload_manual_bank_statement.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_gmail_integration_opportunity.py",
                "tests/test_communication/test_api/test_slack_preference_override.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_hris/test_models.py",
                "tests/test_async_job/test_routes.py",
                "tests/test_banking/test_api/test_update_manual_bank_connections.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py"
            ],
            [
                "tests/test_banking/test_api/test_list_accounts.py",
                "tests/test_approvals_v2/test_services.py",
                "tests/test_spend_allocations/test_api/test_spend_programs_api.py",
                "tests/test_event_history/test_bill_api.py",
                "tests/test_vendor_network/test_dao.py",
                "tests/test_utils/test_auth/test_auth_decorators.py",
                "tests/test_transfer/test_services.py",
                "tests/test_flex/test_dao/test_flex_check_payments.py",
                "tests/test_mailbox/test_celery.py",
                "tests/test_transaction/test_api/test_chargeback_event_handling.py",
                "tests/test_webhooks/marqeta/test_mixins/test_marqeta_card_transitions.py",
                "tests/test_banking/test_linking/test_providers/test_finicity/test_ach_numbers.py",
                "tests/test_external_firm/routes/public_api/test_public_invite_routes.py",
                "tests/test_invite/test_api/test_listing_invites.py",
                "tests/test_banking/test_heron_integration/test_heron_proxy_utils.py",
                "tests/test_payments/test_services/test_providers/test_dates.py",
                "tests/test_profile/test_api/test_admin_combine_identities.py",
                "tests/test_merchant/test_api/test_renaming_request.py",
                "tests/test_external_firm/_internal/services/test_authorizations.py",
                "tests/test_invoices/test_services.py",
                "tests/test_flex/test_statements/test_pdf_formatter.py",
                "tests/test_issuing/test_services/test_create_card.py",
                "tests/test_invite/test_api/test_admin_invite_revocation.py",
                "tests/test_flex/test_public_api/test_risk_holds.py",
                "tests/test_webhooks/marqeta/test_api/test_tokenization.py",
                "tests/test_ledger/test_internal/test_dao/test_balances.py",
                "tests/test_communication/test_schemas.py",
                "tests/test_referral/test_api/test_dao.py",
                "tests/test_communication/test_api/test_slack_receipt_upload.py",
                "tests/test_merchant/test_dao/test_delete_all_but_most_recent_predictions_for_business.py",
                "tests/test_stripe/test_db_routines/test_new_stripe_transaction.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_billing/test_services/test_create_active_or_trial_subscription.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_banking/test_api/test_update_manual_bank_connections.py",
                "tests/test_qbr/services/test_is_business_eligible_for_qbr.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_transaction/test_services/test_should_file_dispute.py",
                "tests/test_accounting/test_iif_generator.py",
                "tests/test_transaction_interactions/test_services/test_expense_policy_interaction_service.py",
                "tests/test_flex/test_public_api/test_entities_eligibility.py",
                "tests/test_business/test_api/test_summary.py",
                "tests/test_savings/test_dao.py",
                "tests/test_event_history/test_reimbursement_api.py",
                "tests/test_card/test_models/test_reissuance.py",
                "tests/test_flex/test_clients/test_banking/test_public_api.py",
                "tests/test_event_history/test_card_api.py",
                "tests/test_spend_allocations/test_services/test_creation_services.py",
                "tests/test_accounting/test_lists/test_seek_and_destroy_duplicates.py",
                "tests/test_delinquency/test_service.py",
                "tests/test_flex/test_celery_tasks/test_build_salesforce_payload.py",
                "tests/test_celery/test_communicate/test_communicate_to_admin_new_spend_allocation_restricted_card_request.py",
                "tests/test_spend_allocations/test_services/test_spend_program_migration_services.py",
                "tests/test_switching/test_api/test_admin_api.py",
                "tests/test_card/test_api/test_schemas.py",
                "tests/test_flex/test_admin_api/test_supress_limit_utilization_alert.py",
                "tests/test_transfer/test_api/test_admin_payment_installment.py",
                "tests/test_hris/test_merge_api.py",
                "tests/test_developer/test_receipt_integrations/test_receipt_integrations_api.py",
                "tests/test_card/test_models/test_card_event.py",
                "tests/test_magic_link/test_admin_api.py",
                "tests/test_workflows/test_services/test_sdk/test_full_sdk_translation.py",
                "tests/test_delinquency/test_admin_api.py",
                "tests/test_incentives/test_utils.py",
                "tests/test_bill_pay/test_services/test_accounting_schema.py",
                "tests/test_utils/test_auth/test_jwt.py",
                "tests/test_qbr/test_opportunities/test_renderer.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_utils/test_group_pagination.py",
                "tests/test_communication/test_api/test_slack_app_home_tab.py",
                "tests/test_okta_scim/test_dao.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py"
            ],
            [
                "tests/test_transaction/test_services/test_dispute_filing.py",
                "tests/test_payee/test_dao/test_core.py",
                "tests/test_transaction/test_api/test_export_transactions.py",
                "tests/test_bill_pay/test_matching/test_services.py",
                "tests/test_accounting/test_resolve_transaction_canonical_provider_location.py",
                "tests/test_accounting/test_match_card_to_bill/test_dao.py",
                "tests/test_payments/test_clients/test_wise.py",
                "tests/test_accounting/test_attribution/test_attribution_consistent_with_multiple_accesses.py",
                "tests/test_flex/test_clients/test_banking/test_public_api.py",
                "tests/test_celery/test_banking/test_bank_statements/test_common_bank_statement_tasks.py",
                "tests/test_accounting/test_providers/test_xero/test_client.py",
                "tests/test_financing_application/test_dao.py",
                "tests/test_flex/test_public_api/test_selected_offer_for_entity.py",
                "tests/test_merchant/test_dao/test_merchants_for_business.py",
                "tests/test_receipt/test_celery.py",
                "tests/test_celery/test_banking/test_manual_statement_tasks.py",
                "tests/test_celery/test_slack_communication/test_send_reminders_to_finish_slack_set_up.py",
                "tests/test_checklist/test_checkers/test_checker_industry_taxonomy_is_correct.py",
                "tests/test_qbr/public_api/test_opportunities_resource.py",
                "tests/test_celery/test_card_reset.py",
                "tests/test_transaction/test_api/test_import_transactions.py",
                "tests/test_issuing/test_services/test_create_card.py",
                "tests/test_invite/test_api/test_admin_invite_revocation.py",
                "tests/test_authentication/test_api/test_admin_api.py",
                "tests/test_webhooks/marqeta/test_api/test_tokenization.py",
                "tests/test_profile/test_dao/test_permissions.py",
                "tests/test_fraud/test_dao/test_fraud_alerts.py",
                "tests/test_approval_policy/api/test_admin_api.py",
                "tests/test_reimbursement/test_api/test_reimbursement_enablement.py",
                "tests/test_demo/test_create_fixture_business.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_hris_opportunity.py",
                "tests/test_profile/test_models/test_cardholder_agreement.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_accounting/test_providers/test_netsuite_rest/test_types.py",
                "tests/test_flex/test_public_api/test_get_state_amount.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_accounting/test_lists/test_apis/test_cardholder_can_select_none.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_customer_management/test_tasks.py",
                "tests/test_stripe/test_transaction_original_amount.py",
                "tests/test_developer/test_spend_limit/test_spend_limit_api.py",
                "tests/test_celery/test_payee/test_payee_tasks.py",
                "tests/test_communication/test_api/test_slack_user_responds_to_reimbursement_request.py",
                "tests/test_approval_policy/test_dao.py",
                "tests/test_business/test_api/test_departments.py",
                "tests/test_merchant/test_api/test_saas_spend_with_stored_merchants.py",
                "tests/test_webhooks/test_services.py",
                "tests/test_backfills/instances/test_deactivate_mq_cardholders_with_no_mq_cards_20230608100001.py",
                "tests/test_loan_origination/test_dao/test_loan.py",
                "tests/test_payments/test_dao/test_fees.py",
                "tests/test_invite/test_schemas/test_invite_schema.py",
                "tests/test_card/test_validation/test_card_validation.py",
                "tests/test_transaction/test_utils.py",
                "tests/test_flex/test_services/test_lock_in_flex_for_bill.py",
                "tests/test_developer/test_token/test_token_api.py",
                "tests/test_checklist/test_checkers/test_checker_kyc_individuals_all_passing.py",
                "tests/test_qbr/test_opportunities/test_compliance_opportunities/test_approval_policy_opportunity.py",
                "tests/test_accounting/test_lists/test_apis/test_remote_account.py",
                "tests/test_celery/test_transaction.py",
                "tests/test_checklist/test_checkers/test_checker_has_confirmed_dnb_file.py",
                "tests/test_communication/test_slack_communication/test_update_slack_spend_allocation_request_verdict.py",
                "tests/test_customer/test_spacex.py",
                "tests/test_banking/test_utils.py",
                "tests/test_banking/test_remove_duplicate_accounts_for_business.py",
                "tests/test_external_firm/_internal/services/test_firm_application.py",
                "tests/test_referral/test_api/test_dao.py",
                "tests/test_utils/test_sessions.py",
                "tests/test_merchant/test_dao/test_delete_all_but_most_recent_predictions_for_business.py",
                "tests/test_stripe/test_db_routines/test_new_stripe_transaction.py",
                "tests/test_qbr/test_report/test_render_primary_indicator_summary.py",
                "tests/test_billing/test_services/test_create_active_or_trial_subscription.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_accounting/test_providers/test_sage/test_provider_context.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_accounting/test_lists/test_apis/test_cardholder_can_select_none.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_metrics/test_transaction_metrics/test_api/test_transactions_metrics.py",
                "tests/test_financing_application/test_api/test_admin_api.py",
                "tests/test_external_firm/routes/public_api/test_public_api.py",
                "tests/test_financing_application/test_services.py",
                "tests/test_receipt/test_dao.py",
                "tests/test_spend_request/test_services.py",
                "tests/test_flex/test_public_api/test_installment_payment_request.py",
                "tests/test_statement/test_models/test_statements.py",
                "tests/test_event_history/test_spend_allocation_api.py",
                "tests/test_profile/test_api/test_invited_user_registers.py",
                "tests/test_communication/test_api/test_business_communication_preferences_update.py",
                "tests/test_flex/test_services/test_fee_refunds.py",
                "tests/test_ecommerce/test_tasks/test_delete_rutter_connection.py",
                "tests/test_transaction/test_tasks/test_disputes.py",
                "tests/test_banking/test_linking/test_providers/test_finicity/test_failures.py",
                "tests/test_celery/test_communicate/test_communicate_transaction_notification_for_approval_chain.py",
                "tests/test_flex/test_clients/test_bill_pay/test_flex_utils.py",
                "tests/test_flex/test_celery_tasks/test_installment_payment_failure.py",
                "tests/test_ledger/test_services/test_entries.py",
                "tests/test_accounting/test_sync/test_sync_statement_credit.py",
                "tests/test_banking/test_api/test_user_ach_debit_check.py",
                "tests/test_stale_gla/test_treatment/test_tasks.py",
                "tests/test_profile/test_api/test_legal_acceptance.py",
                "tests/test_celery/test_communicate/test_communicate_card_unlocked.py",
                "tests/test_communication_platform/test_communication_platform_tasks/test_sending.py",
                "tests/test_profile/test_dao/test_permissions.py",
                "tests/test_internal_tooling/test_inbound_user_communication/test_service.py",
                "tests/test_flex/test_dao/test_flex_payment_transfer.py",
                "tests/test_utils/test_sessions.py",
                "tests/test_demo/test_create_fixture_business.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_hris_opportunity.py",
                "tests/test_banking/test_api/test_legal_terms.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_profile/test_api/test_user_preferences.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_migrations.py",
                "tests/test_accounting/test_sync/test_transaction_utils.py",
                "tests/test_approval_policy/api/test_apply_card_actions.py",
                "tests/test_payments/test_clients/test_increase.py",
                "tests/test_payee/test_services/test_payee_services.py",
                "tests/test_banking/test_dao.py",
                "tests/test_spend_allocations/test_dao/test_spend_program_visibility.py",
                "tests/test_flex/test_public_api/test_retry_payment.py",
                "tests/test_banking/test_linking/test_daos/test_finicity/test_stale_temporary_error_accounts.py",
                "tests/test_expense_policy/test_dao.py",
                "tests/test_internal_tooling/test_operational_definitions/test_user/test_dao.py",
                "tests/test_statement/test_services/test_payments.py",
                "tests/test_profile/test_api/test_copilot_crud.py",
                "tests/test_approval_policy/services/test_handling_user_role_changes.py",
                "tests/test_banking/test_api/test_inscribe_bank_evals.py",
                "tests/test_celery/test_spend_request.py",
                "tests/test_card/test_schemas/test_card_schema.py",
                "tests/test_accounting/test_api/test_provider_merchant_map.py",
                "tests/test_accounting/test_api/test_get_deep_link.py",
                "tests/test_banking/test_api/test_user_bank_account_international.py",
                "tests/test_loan_origination/test_services/test_loan.py",
                "tests/test_checklist/test_checkers/test_checker_kyc_business_passing.py",
                "tests/test_accounting/test_api/test_providers_multiple.py",
                "tests/test_negotiations/api/test_public_api.py",
                "tests/test_communication_platform/test_communication_platform_tasks/test_sending.py",
                "tests/test_profile/test_dao/test_permissions.py",
                "tests/test_internal_tooling/test_inbound_user_communication/test_service.py",
                "tests/test_financing_application/test_task_payload_utils.py",
                "tests/test_accounting/test_filters/test_apis/test_display_tracking_category_options.py",
                "tests/test_communication/test_services.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_utils/test_group_pagination.py",
                "tests/test_communication/test_api/test_slack_app_home_tab.py",
                "tests/test_financing_application/test_api/test_sales_lead_api.py",
                "tests/test_accounting/test_providers/test_netsuite_rest/test_types.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_accounting/test_providers/test_sage/test_provider_context.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_spend/test_spend_events/test_backfill.py",
                "tests/test_communication/test_api/test_slack_last_four_reply.py",
                "tests/test_bill_pay/test_api/test_approvals_v2.py",
                "tests/test_policy/test_api/test_public_api.py",
                "tests/test_spend_request/test_request_services.py",
                "tests/test_external_firm/routes/public_api/test_public_authorization_routes.py",
                "tests/test_business/test_api/test_departments.py",
                "tests/test_billing/test_statement_generation/test_pdf_statement_generation.py",
                "tests/test_developer/test_department/test_department_api.py",
                "tests/test_transaction/test_services/test_transaction_approval_chains.py",
                "tests/test_approval_policy/services/test_compute_user_actions_metadata_tuple.py",
                "tests/test_transaction/test_api/test_fraud_response.py",
                "tests/test_transaction/test_api/test_taxes.py",
                "tests/test_transaction/test_dao/test_get_transactions_limited_by_user.py",
                "tests/test_issuing/test_utils.py",
                "tests/test_communication/test_api/test_application_approval_confirmation.py",
                "tests/test_rules/test_services.py",
                "tests/test_developer/test_receipt/test_receipt_api.py",
                "tests/test_accounting/test_saas_hooks.py",
                "tests/test_alerts/test_models.py",
                "tests/test_payee/test_services/test_documents.py",
                "tests/test_webhooks/test_travel_receipt.py",
                "tests/test_business/test_api/test_admin_delete_department.py",
                "tests/test_banking/test_api/test_get_transaction_categorization.py",
                "tests/test_flex/test_admin_api/test_risk_premia_eligibility.py",
                "tests/test_delinquency/test_admin_api.py",
                "tests/test_accounting/test_api/test_refresh_tracking_categories.py",
                "tests/test_qbr/public_api/test_dismiss_opportunities_resource.py",
                "tests/test_banking/test_models.py",
                "tests/test_qbr/test_opportunities/test_renderer.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_utils/test_group_pagination.py",
                "tests/test_communication/test_api/test_slack_app_home_tab.py",
                "tests/test_okta_scim/test_dao.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_business/test_api/test_currency_settings.py",
                "tests/test_docs/test_restx.py",
                "tests/test_docs/test_restx.py"
            ],
            [
                "tests/test_capital_markets/test_services.py",
                "tests/test_celery/test_financing_application_tasks.py",
                "tests/test_travel/test_public_api.py",
                "tests/test_accounting/test_mapping/test_utils.py",
                "tests/test_celery/test_communicate/test_communicate_new_bill_pay_request.py",
                "tests/test_policy/test_services.py",
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_refresh_transaction_canonical_canada.py",
                "tests/test_banking/test_linking/test_providers/test_finicity/test_main_flow.py",
                "tests/test_flex/test_admin_api/test_flex_installment_payment_pause.py",
                "tests/test_flex/test_services/test_onboarding.py",
                "tests/test_hris/test_dao.py",
                "tests/test_webhooks/marqeta/test_mixins/test_marqeta_chargeback_events_handler.py",
                "tests/test_invite/test_schemas/test_invite_schema.py",
                "tests/test_developer/test_card/test_celery.py",
                "tests/test_checklist/test_checkers/test_checker_all_bank_accounts_verified.py",
                "tests/test_celery/test_teller_personal_tasks.py",
                "tests/test_communication/test_user_communication/test_missing_items_needed.py",
                "tests/test_receipt/test_api/test_retrieve_receipt.py",
                "tests/test_magic_link/test_vendor_upload_payment_details.py",
                "tests/test_data_export_async_job/test_api.py",
                "tests/test_proxies/authorizer/test_utils.py",
                "tests/test_transaction/test_services/test_dispute_comms.py",
                "tests/test_receipt/_internal/matching/test_receipt_processing.py",
                "tests/test_proxies/authorizer/test_authorizer.py",
                "tests/test_celery/test_incentives.py",
                "tests/test_celery/test_communicate/test_communicate_verify_email.py",
                "tests/test_transaction/test_dao/test_is_transaction_freshly_authorized.py",
                "tests/test_negotiations/api/test_admin_api.py",
                "tests/test_receipt/test_date_extractor.py",
                "tests/test_customer_management/test_schema.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_qbr/test_opportunities/test_compliance_opportunities/test_submission_policy_opportunity.py",
                "tests/test_profile/test_utils/test_scope_lifetime_helpers.py",
                "tests/test_billing/test_public_api/test_settings.py",
                "tests/test_profile/test_api/test_user_preferences.py",
                "tests/test_external_firm/test_external_firm_user_model.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_flex/test_services/test_balance.py"
            ],
            [
                "tests/test_customer_management/test_admin_api.py",
                "tests/test_flex/test_celery_tasks/test_update_installment_status.py",
                "tests/test_flex/test_celery_tasks/test_flex_high_risk_flexes.py",
                "tests/test_celery/test_communicate/test_communicate_transaction.py",
                "tests/test_celery/test_banking/test_heron/test_queue_new_finicity_transactions_for_heron.py",
                "tests/test_spend_allocations/test_api/test_export_spend_allocations.py",
                "tests/test_accounting/test_reports/test_services.py",
                "tests/test_currency/test_api.py",
                "tests/test_spend_allocations/test_api/test_spend_allocation_policy.py",
                "tests/test_bill_pay/test_card_services.py",
                "tests/test_flex/test_dao/test_get_entities_in_range.py",
                "tests/test_communication/test_channels/test_slack_external.py",
                "tests/test_webhooks/test_zendesk_webhooks.py",
                "tests/test_bill_pay/test_bill_payments.py",
                "tests/test_checklist/test_checkers/test_checker_all_bank_accounts_verified.py",
                "tests/test_metrics/test_spend/test_utils.py",
                "tests/test_payments/test_celery/test_wise.py",
                "tests/test_developer/test_reimbursement/test_reimbursement_api.py",
                "tests/test_checklist/test_checkers/test_checker_no_entity_with_shared_accounts.py",
                "tests/test_banking/test_api/test_user_bank_account.py",
                "tests/test_fraud/test_ofac_checks/test_services.py",
                "tests/test_checklist/test_checkers/test_checker_has_confirmed_dnb_file.py",
                "tests/test_communication/test_slack_communication/test_update_slack_spend_allocation_request_verdict.py",
                "tests/test_celery/test_banking/test_daily_account_tasks.py",
                "tests/test_hris/test_invite.py",
                "tests/test_authentication/test_api/test_public_api.py",
                "tests/test_celery/test_communicate/test_communicate_monthly_spend_report.py",
                "tests/test_referral/services/test_payouts_services.py",
                "tests/test_profile/test_create_user/test_create_invited_user.py",
                "tests/test_partner_rewards/test_dao.py",
                "tests/test_delinquency/test_tasks.py",
                "tests/test_spend_allocations/test_utils/test_spend_allocation_restrictions.py",
                "tests/test_billing/test_services/test_decorators.py",
                "tests/test_authz/test_services.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_flex/test_public_api/test_get_state_amount.py",
                "tests/test_leads/test_api/test_enrich_lead.py",
                "tests/test_webhooks/test_increase_webhooks.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_communication/test_admin_communication/test_daily_digest/test_dao.py",
                "tests/test_communication/test_api/test_slack_user_responds_to_card_request.py",
                "tests/test_spend/test_spend_events/test_public_api.py",
                "tests/test_flex/test_services/test_flex_status.py",
                "tests/test_celery/test_communicate/test_weekly_transactions_needing_attention.py",
                "tests/test_billing/test_services/test_subscriptions.py",
                "tests/test_transaction/test_api/test_repayments.py",
                "tests/test_business/test_api/test_locations.py",
                "tests/test_external_firm/routes/admin_api/test_migratable_firm_users_api.py",
                "tests/test_receipt_integrations/test_services/test_services.py",
                "tests/test_approval_policy/services/test_compute_user_actions_metadata_tuple.py",
                "tests/test_communication/test_slack_communication/test_restricted_card_request_verdict.py",
                "tests/test_developer/test_transfer/test_transfer_api.py",
                "tests/test_business/test_api/test_list_user_cards.py",
                "tests/test_receipt/test_api/test_admin_api.py",
                "tests/test_webhooks/marqeta/test_mixins/test_marqeta_chargebacktransitions_webhook.py",
                "tests/test_incentives/test_api/test_public_api.py",
                "tests/test_fraud/test_transaction/test_confirm_transaction_is_fraud.py",
                "tests/test_flex/test_celery_tasks/test_offer_acceptance.py",
                "tests/test_invoices/test_services.py",
                "tests/test_hris/test_merge_api.py",
                "tests/test_external_firm/services/test_add_self_assigned_spend_user.py",
                "tests/test_card/test_models/test_card_event.py",
                "tests/test_celery/test_communicate/test_communicate_card_unlocked.py",
                "tests/test_communication_platform/test_communication_platform_tasks/test_sending.py",
                "tests/test_transaction/test_model/test_models.py",
                "tests/test_issuing/test_ip_address_backfill.py",
                "tests/test_banking/test_api/test_get_manual_bank_statement_metadata.py",
                "tests/test_banking/test_models.py",
                "tests/test_qbr/test_opportunities/test_renderer.py",
                "tests/test_referral/_internal/services/test_referred_business.py",
                "tests/test_utils/test_group_pagination.py",
                "tests/test_communication/test_api/test_slack_app_home_tab.py",
                "tests/test_okta_scim/test_dao.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_loan_origination/test_services/test_loan_state_machine.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py"
            ],
            [
                "tests/test_reimbursement/test_services.py",
                "tests/test_merchant/test_api/test_list_saas_spend.py",
                "tests/test_stale_gla/test_treatment/test_services.py",
                "tests/test_celery/test_alerts.py",
                "tests/test_accounting/test_financial_statements/test_financial_statements.py",
                "tests/test_developer/test_user/test_user_api.py",
                "tests/test_custom_form/test_services/test_services.py",
                "tests/test_switching/test_api/test_public_api.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_accounting_rule_opportunity.py",
                "tests/test_ftux/test_public_api.py",
                "tests/test_reimbursement/test_api/test_taxes.py",
                "tests/test_receipt/test_api/test_upload_receipt.py",
                "tests/test_merchant/test_api/test_export_saas_spend.py",
                "tests/test_transfer/test_api/test_debit_check_status.py",
                "tests/test_savings/test_task.py",
                "tests/test_card/test_utils/test_update_card_owner.py",
                "tests/test_celery/test_banking/test_business_manual_account_creation_tasks.py",
                "tests/test_external_firm/_internal/services/test_firm_deletion.py",
                "tests/test_flex/test_admin_api/test_supress_limit_utilization_alert.py",
                "tests/test_celery/test_card_reset.py",
                "tests/test_external_firm/test_external_firm_authorization_model.py",
                "tests/test_transaction/test_api/test_currency_conversion.py",
                "tests/test_banking/test_api/test_bank_balance_update_manual.py",
                "tests/test_financing_application/test_api/test_checklist_create_evaluation.py",
                "tests/test_banking/test_utils.py",
                "tests/test_celery/test_slack_communication/test_communicate_weekly_reminder.py",
                "tests/test_accounting/test_lists/test_utils.py",
                "tests/test_backfills/instances/test_backfill_won_mq_merchant_disputes_20230621175158.py",
                "tests/test_celery/test_fraud/test_log_ofac_checks.py",
                "tests/test_partner_rewards/test_dao.py",
                "tests/test_delinquency/test_tasks.py",
                "tests/test_invoices/test_tasks.py",
                "tests/test_billing/test_services/test_decorators.py",
                "tests/test_communication/test_api/test_notify_by_push_notification_admin.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_billing/test_services/test_settings.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_celery/test_stripe.py",
                "tests/test_communication/test_slack_communication/test_accept_spend_allocation_request.py",
                "tests/test_accounting/test_workflows/test_option_filtering.py",
                "tests/test_communication/test_slack_communication/test_receipt_memo_submission.py",
                "tests/test_card/test_api/test_card_reissuance.py",
                "tests/test_payments/test_api/test_admin_api.py",
                "tests/test_loan_origination/test_celery_tasks/test_loan_sales_response.py",
                "tests/test_statement/test_services/test_billing_date.py",
                "tests/test_accounting/test_api/test_mapping_rules.py",
                "tests/test_approval_policy/services/test_deduping_approval_chains.py",
                "tests/test_hris/test_admin_api.py",
                "tests/test_card/test_services/test_services.py",
                "tests/test_webhooks/test_zendesk_webhooks.py",
                "tests/test_issuing/test_services/test_create_cardholder.py",
                "tests/test_internal_tooling/test_linear_integration/test_linear_client.py",
                "tests/test_referral/test_api/test_referrals_public_api.py",
                "tests/test_loan_origination/test_celery_tasks/test_beneficial_owner_daily.py",
                "tests/test_celery/test_slack_communication/test_slack_send_welcome_message_to_all_ramp_users.py",
                "tests/test_receipt/test_text_based_match/test_amount_match.py",
                "tests/test_profile/test_api/test_receipt_upload_email_address.py",
                "tests/test_communication/test_dao.py",
                "tests/test_celery/test_communicate/test_communicate_invitation_to_join_team.py",
                "tests/test_receipt/_internal/matching/test_receipt_processing.py",
                "tests/test_checklist/test_checkers/test_checker_passes_fraud_scorecard.py",
                "tests/test_webhooks/marqeta/test_api/test_tokenization.py",
                "tests/test_transaction/test_services/test_dispute_evidence.py",
                "tests/test_flex/test_celery_tasks/test_move_businesses_off_waitlist.py",
                "tests/test_negotiations/api/test_admin_api.py",
                "tests/test_utils/test_auth/test_jwt.py",
                "tests/test_vendor_network/test_api/test_address_api.py",
                "tests/test_communication/test_api/test_slack_preference_override.py",
                "tests/test_balance/test_services/test_get_limits.py",
                "tests/test_billing/test_services/test_create_active_or_trial_subscription.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_banking/test_api/test_update_manual_bank_connections.py",
                "tests/test_banking/test_api/test_bank_account_subtype_update.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_flex/test_admin_api/test_update_risk_policy_outcome_for_business.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_card/test_utils/test_process_restricted_card_request_update.py",
                "tests/test_accounting/test_providers/test_netsuite_rest/test_client.py",
                "tests/test_flex/test_celery_tasks/test_collect_outstanding_installments.py",
                "tests/test_financing_application/test_tasks.py",
                "tests/test_hris/test_public_api.py",
                "tests/test_magic_link/test_api.py",
                "tests/test_profile/test_api/test_current.py",
                "tests/test_internal_tooling/test_ivr_authentication/test_webhooks_api.py",
                "tests/test_qbr/test_opportunities/test_operational_efficiency_opportunities/test_accounting_rule_opportunity.py",
                "tests/test_external_firm/test_spend_user_authorization_restrictions.py",
                "tests/test_reimbursement/test_api/test_reimbursement_policies.py",
                "tests/test_capital_markets/test_dao.py",
                "tests/test_accounting/test_lists/test_apis/test_list_payments.py",
                "tests/test_invite/test_api/test_listing_invites.py",
                "tests/test_spend_allocations/test_dao/test_spend_allocation_balances.py",
                "tests/test_spend_allocations/test_dao/test_spend_allocation_curriences.py",
                "tests/test_celery/test_banking/test_ops_tasks.py",
                "tests/test_magic_link/test_services.py",
                "tests/test_card/test_api/test_card_category_and_vendor_copy.py",
                "tests/test_banking/test_api/test_user_bank_account.py",
                "tests/test_flex/test_admin_api/test_estimated_fees_for_business.py",
                "tests/test_accounting/test_lists/test_apis/test_account_usage_type.py",
                "tests/test_banking/test_api/test_delete_account.py",
                "tests/test_negotiations/api/test_public_api.py",
                "tests/test_receipt/_internal/matching/test_merchant_specific_matching.py",
                "tests/test_billing/test_celery_tasks/test_cycle_statements.py",
                "tests/test_fixtures/test_fixture_users.py",
                "tests/test_negotiations/api/test_admin_api.py",
                "tests/test_payments/test_services/test_providers/test_lob.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_gmail_integration_opportunity.py",
                "tests/test_communication/test_api/test_slack_preference_override.py",
                "tests/test_external_firm/tasks/reminder/test_daily_reminder_pending_external_firm_proposal.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_communication/test_api/test_notify_by_push_notification_admin.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_transaction/test_dao/test_refresh_transaction_canonical/test_original_amount.py",
                "tests/test_communication/test_api/test_slack_card_request.py",
                "tests/test_loan_origination/test_celery_tasks/test_loan_origination_request.py",
                "tests/test_vendor_network/test_api/test_bill_api.py",
                "tests/test_flex/test_integration/test_single_legged_happy_path.py",
                "tests/test_magic_link/test_api.py",
                "tests/test_celery/test_communicate/test_communicate_to_user_restricted_spend_allocation_verdict.py",
                "tests/test_flex/test_admin_api/test_finalize_financing_for_bill.py",
                "tests/test_spend/test_spend_events/test_transaction_canonical_triggers.py",
                "tests/test_transaction/test_services/test_transaction_approval_chains.py",
                "tests/test_accounting/test_dao.py",
                "tests/test_business/test_api/test_manager_remove_user.py",
                "tests/test_stripe/test_stripe_logos.py",
                "tests/test_transaction/test_api/test_admin_api.py",
                "tests/test_internal_tooling/test_ivr_authentication/test_dao.py",
                "tests/test_card/test_utils/test_create_card.py",
                "tests/test_payments/test_clients/test_jpm.py",
                "tests/test_expense_policy/test_public_api.py",
                "tests/test_external_firm/_internal/services/test_authorizations.py",
                "tests/test_internal_tooling/test_admin_api.py",
                "tests/test_banking/test_api/test_admin_api_bank_account_test_routes.py",
                "tests/test_ledger/test_clients/test_fragment.py",
                "tests/test_accounting/test_coding_v2/test_services.py",
                "tests/test_flex/test_dao/test_risk_holds.py",
                "tests/test_communication_platform/test_communication_platform_tasks/test_sending.py",
                "tests/test_banking/test_remove_duplicate_accounts_for_business.py",
                "tests/test_loan_origination/test_dao/test_loan_payment.py",
                "tests/test_referral/test_api/test_dao.py",
                "tests/test_utils/test_sessions.py",
                "tests/test_merchant/test_dao/test_delete_all_but_most_recent_predictions_for_business.py",
                "tests/test_profile/test_models/test_user_identity_trigger.py",
                "tests/test_communication_platform/test_clients/test_push_notification_client.py",
                "tests/test_webhooks/test_webflow_webhooks.py",
                "tests/test_communication/test_api/test_notify_by_push_notification_admin.py",
                "tests/test_issuing/test_services/test_delete_cardholders.py",
                "tests/test_qbr/test_opportunities/test_savings_opportunities/test_negotiations_opportunity.py",
                "tests/test_business/test_api/test_ftux_limits.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_banking/test_api/test_update_whitelists.py",
                "tests/test_utils/test_utils.py",
                "tests/test_business/test_dao/test_bank_referrals.py",
                "tests/test_stripe/test_stripe_utils.py"
            ],
            [
                "tests/test_missing_items_wizard/test_api/test_public_api.py",
                "tests/test_celery/test_banking_tasks.py",
                "tests/test_card/test_api/test_admin_card_create.py",
                "tests/test_invite/test_api/test_create_invite.py",
                "tests/test_transfer/test_jpm_services.py",
                "tests/test_payments/test_dao/test_dao.py",
                "tests/test_card/test_api/test_admin_ap_card_issuance.py",
                "tests/test_accounting/test_api/test_financial_statement_crud.py",
                "tests/test_restrictions/test_dao.py",
                "tests/test_accounting/test_sync/test_get_transaction_canonical_id_to_accounting_coding.py",
                "tests/test_celery/test_accounting/test_refresh_accounting_resolution_cache.py",
                "tests/test_card/test_api/test_in_app_provisioning.py",
                "tests/test_receipt/test_verify_receipt.py",
                "tests/test_business/test_api/test_change_direct_manager.py",
                "tests/test_incentives/test_dao.py",
                "tests/test_flex/test_dao/test_offers.py",
                "tests/test_customer_management/test_decorators.py",
                "tests/test_celery/test_slack_communication/test_slack_send_welcome_message_to_all_ramp_users.py",
                "tests/test_business/test_api/test_remove_user.py",
                "tests/test_profile/test_api/test_receipt_upload_email_address.py",
                "tests/test_financing_application/test_api/test_update_ach_numbers.py",
                "tests/test_celery/test_communicate/test_communicate_invitation_to_join_team.py",
                "tests/test_receipt/_internal/matching/test_receipt_processing.py",
                "tests/test_flex/test_dao/test_risk_holds.py",
                "tests/test_webhooks/marqeta/test_api/test_tokenization.py",
                "tests/test_transaction/test_services/test_dispute_evidence.py",
                "tests/test_flex/test_admin_api/test_register_waitlist.py",
                "tests/test_proxies/test_ocr/test_scale_client/test_scale_client.py",
                "tests/test_celery/test_fraud/test_log_ofac_checks.py",
                "tests/test_qbr/test_opportunities/test_employee_efficiency/test_outlook_integration_opportunity.py",
                "tests/test_bill_pay/test_services/test_vendor_import.py",
                "tests/test_qbr/test_report/test_render_primary_indicator_summary.py",
                "tests/test_profile/test_api/test_user_audit_log_model.py",
                "tests/test_external_firm/services/test_dao.py",
                "tests/test_approval_policy/services/test_spend_request_services.py",
                "tests/test_webhooks/stripe/test_replay_stripe_event.py",
                "tests/test_external_firm/test_deleted_entity_model.py",
                "tests/test_utils/test_admin_api_auth.py",
                "tests/test_profile/test_dao/test_user_change_request.py",
                "tests/test_utils/test_read_replica_session.py",
                "tests/test_ledger/test_internal/test_services/test_ledgers.py",
                "tests/test_stripe/test_stripe_utils.py"
            ]
            ]
        
        self.paths = [','.join(path) for path in paths]

    def rsync_roots(self, gateway):
        """Rsync the set of roots to the node's gateway cwd."""
        if self.roots:
            for root in self.roots:
                self.rsync(gateway, root, **self.rsyncoptions)

    def setup_nodes(self, putevent):
        start_time = time.time()
        self.config.hook.pytest_xdist_setupnodes(config=self.config, specs=self.specs)
        self.trace("setting up nodes")
        to_return = [self.setup_node(spec, putevent, self.paths[i]) for i, spec in enumerate(self.specs)]
        end_time = time.time()
        self.log("setup_nodes", end_time - start_time)
        return to_return

    def setup_node(self, spec, putevent, path):
        gw = self.group.makegateway(spec)
        self.config.hook.pytest_xdist_newgateway(gateway=gw)
        self.rsync_roots(gw)
        node = WorkerController(self, gw, self.config, putevent, path)
        gw.node = node  # keep the node alive
        node.setup()
        self.trace("started node %r" % node)
        return node

    def teardown_nodes(self):
        self.group.terminate(self.EXIT_TIMEOUT)

    def _getxspecs(self):
        return [execnet.XSpec(x) for x in parse_spec_config(self.config)]

    def _getrsyncdirs(self) -> List[Path]:
        for spec in self.specs:
            if not spec.popen or spec.chdir:
                break
        else:
            return []
        import pytest
        import _pytest

        def get_dir(p):
            """Return the directory path if p is a package or the path to the .py file otherwise."""
            stripped = p.rstrip("co")
            if os.path.basename(stripped) == "__init__.py":
                return os.path.dirname(p)
            else:
                return stripped

        pytestpath = get_dir(pytest.__file__)
        pytestdir = get_dir(_pytest.__file__)
        config = self.config
        candidates = [pytestpath, pytestdir]
        candidates += config.option.rsyncdir
        rsyncroots = config.getini("rsyncdirs")
        if rsyncroots:
            candidates.extend(rsyncroots)
        roots = []
        for root in candidates:
            root = Path(root).resolve()
            if not root.exists():
                raise pytest.UsageError(f"rsyncdir doesn't exist: {root!r}")
            if root not in roots:
                roots.append(root)
        return roots

    def _getrsyncoptions(self):
        """Get options to be passed for rsync."""
        ignores = list(self.DEFAULT_IGNORES)
        ignores += [str(path) for path in self.config.option.rsyncignore]
        ignores += [str(path) for path in self.config.getini("rsyncignore")]

        return {
            "ignores": ignores,
            "verbose": getattr(self.config.option, "verbose", 0),
        }

    def rsync(self, gateway, source, notify=None, verbose=False, ignores=None):
        """Perform rsync to remote hosts for node."""
        # XXX This changes the calling behaviour of
        #     pytest_xdist_rsyncstart and pytest_xdist_rsyncfinish to
        #     be called once per rsync target.
        rsync = HostRSync(source, verbose=verbose, ignores=ignores)
        spec = gateway.spec
        if spec.popen and not spec.chdir:
            # XXX This assumes that sources are python-packages
            #     and that adding the basedir does not hurt.
            gateway.remote_exec(
                """
                import sys ; sys.path.insert(0, %r)
            """
                % os.path.dirname(str(source))
            ).waitclose()
            return
        if (spec, source) in self._rsynced_specs:
            return

        def finished():
            if notify:
                notify("rsyncrootready", spec, source)

        rsync.add_target_host(gateway, finished=finished)
        self._rsynced_specs.add((spec, source))
        self.config.hook.pytest_xdist_rsyncstart(source=source, gateways=[gateway])
        rsync.send()
        self.config.hook.pytest_xdist_rsyncfinish(source=source, gateways=[gateway])


class HostRSync(execnet.RSync):
    """RSyncer that filters out common files"""

    PathLike = Union[str, "os.PathLike[str]"]

    def __init__(
        self,
        sourcedir: PathLike,
        *,
        ignores: Optional[Sequence[PathLike]] = None,
        **kwargs: object
    ) -> None:
        if ignores is None:
            ignores = []
        self._ignores = [re.compile(fnmatch.translate(os.fspath(x))) for x in ignores]
        super().__init__(sourcedir=Path(sourcedir), **kwargs)

    def filter(self, path: PathLike) -> bool:
        path = Path(path)
        for cre in self._ignores:
            if cre.match(path.name) or cre.match(str(path)):
                return False
        else:
            return True

    def add_target_host(self, gateway, finished=None):
        remotepath = os.path.basename(self._sourcedir)
        super().add_target(gateway, remotepath, finishedcallback=finished, delete=True)

    def _report_send_file(self, gateway, modified_rel_path):
        if self._verbose > 0:
            path = os.path.basename(self._sourcedir) + "/" + modified_rel_path
            remotepath = gateway.spec.chdir
            print(f"{gateway.spec}:{remotepath} <= {path}")


def make_reltoroot(roots: Sequence[Path], args: List[str]) -> List[str]:
    # XXX introduce/use public API for splitting pytest args
    splitcode = "::"
    result = []
    for arg in args:
        parts = arg.split(splitcode)
        fspath = Path(parts[0])
        try:
            exists = fspath.exists()
        except OSError:
            exists = False
        if not exists:
            result.append(arg)
            continue
        for root in roots:
            x: Optional[Path]
            try:
                x = fspath.relative_to(root)
            except ValueError:
                x = None
            if x or fspath == root:
                parts[0] = root.name + "/" + str(x)
                break
        else:
            raise ValueError(f"arg {arg} not relative to an rsync root")
        result.append(splitcode.join(parts))
    return result


class WorkerController:
    ENDMARK = -1

    class RemoteHook:
        @pytest.hookimpl(trylast=True)
        def pytest_xdist_getremotemodule(self):
            return xdist.remote

    def __init__(self, nodemanager, gateway, config, putevent, path):
        config.pluginmanager.register(self.RemoteHook())
        self.nodemanager = nodemanager
        self.putevent = putevent
        self.gateway = gateway
        self.config = config
        self.path = path
        argv = [i for i in sys.argv]
        del argv[1]
        for path in self.path.split(","):
            argv.insert(1, path)
        self.workerinput = {
            "workerid": gateway.id,
            "workercount": len(nodemanager.specs),
            "testrunuid": nodemanager.testrunuid,
            "mainargv": argv,
        }
        self._down = False
        self._shutdown_sent = False
        self.log = Producer(f"workerctl-{gateway.id}", enabled=config.option.debug)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.gateway.id}>"

    @property
    def shutting_down(self):
        return self._down or self._shutdown_sent

    def setup(self):
        self.log("setting up worker session")
        spec = self.gateway.spec
        self.log(spec)
        if hasattr(self.config, "invocation_params"):
            args = [str(x) for x in self.config.invocation_params.args or ()]
            option_dict = {}
        else:
            args = self.config.args
            option_dict = vars(self.config.option)
        if not spec.popen or spec.chdir:
            args = make_reltoroot(self.nodemanager.roots, args)
        if spec.popen:
            name = "popen-%s" % self.gateway.id
            if hasattr(self.config, "_tmp_path_factory"):
                basetemp = self.config._tmp_path_factory.getbasetemp()
                option_dict["basetemp"] = str(basetemp / name)
        self.config.hook.pytest_configure_node(node=self)

        remote_module = self.config.hook.pytest_xdist_getremotemodule()
        self.channel = self.gateway.remote_exec(remote_module)
        # change sys.path only for remote workers
        # restore sys.path from a frozen copy for local workers
        change_sys_path = _sys_path if self.gateway.spec.popen else None
        self.log(self.workerinput, args, option_dict, change_sys_path)
        del args[0]
        for path in self.path.split(","):
            args.insert(0, path)
        self.log(self.workerinput, args, option_dict, change_sys_path)
        self.channel.send((self.workerinput, args, option_dict, change_sys_path))

        if self.putevent:
            self.channel.setcallback(self.process_from_remote, endmarker=self.ENDMARK)

    def ensure_teardown(self):
        if hasattr(self, "channel"):
            if not self.channel.isclosed():
                self.log("closing", self.channel)
                self.channel.close()
            # del self.channel
        if hasattr(self, "gateway"):
            self.log("exiting", self.gateway)
            self.gateway.exit()
            # del self.gateway

    def send_runtest_some(self, indices):
        self.sendcommand("runtests", indices=indices)

    def send_runtest_all(self):
        self.sendcommand("runtests_all")

    def send_steal(self, indices):
        self.sendcommand("steal", indices=indices)

    def shutdown(self):
        if not self._down:
            try:
                self.sendcommand("shutdown")
            except OSError:
                pass
            self._shutdown_sent = True

    def sendcommand(self, name, **kwargs):
        """send a named parametrized command to the other side."""
        self.log(f"sending command {name}(**{kwargs})")
        self.channel.send((name, kwargs))

    def notify_inproc(self, eventname, **kwargs):
        self.log(f"queuing {eventname}(**{kwargs})")
        self.putevent((eventname, kwargs))

    def process_from_remote(self, eventcall):  # noqa too complex
        """this gets called for each object we receive from
        the other side and if the channel closes.

        Note that channel callbacks run in the receiver
        thread of execnet gateways - we need to
        avoid raising exceptions or doing heavy work.
        """
        try:
            if eventcall == self.ENDMARK:
                err = self.channel._getremoteerror()
                if not self._down:
                    if not err or isinstance(err, EOFError):
                        err = "Not properly terminated"  # lost connection?
                    self.notify_inproc("errordown", node=self, error=err)
                    self._down = True
                return
            eventname, kwargs = eventcall
            if eventname in ("collectionstart",):
                self.log(f"ignoring {eventname}({kwargs})")
            elif eventname == "workerready":
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname == "internal_error":
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname == "workerfinished":
                self._down = True
                self.workeroutput = kwargs["workeroutput"]
                self.notify_inproc("workerfinished", node=self)
            elif eventname in ("logstart", "logfinish"):
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname in ("testreport", "collectreport", "teardownreport"):
                item_index = kwargs.pop("item_index", None)
                rep = self.config.hook.pytest_report_from_serializable(
                    config=self.config, data=kwargs["data"]
                )
                if item_index is not None:
                    rep.item_index = item_index
                self.notify_inproc(eventname, node=self, rep=rep)
            elif eventname == "collectionfinish":
                self.notify_inproc(eventname, node=self, ids=kwargs["ids"])
            elif eventname == "runtest_protocol_complete":
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname == "unscheduled":
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname == "logwarning":
                self.notify_inproc(
                    eventname,
                    message=kwargs["message"],
                    code=kwargs["code"],
                    nodeid=kwargs["nodeid"],
                    fslocation=kwargs["nodeid"],
                )
            elif eventname == "warning_captured":
                warning_message = unserialize_warning_message(
                    kwargs["warning_message_data"]
                )
                self.notify_inproc(
                    eventname,
                    warning_message=warning_message,
                    when=kwargs["when"],
                    item=kwargs["item"],
                )
            elif eventname == "warning_recorded":
                warning_message = unserialize_warning_message(
                    kwargs["warning_message_data"]
                )
                self.notify_inproc(
                    eventname,
                    warning_message=warning_message,
                    when=kwargs["when"],
                    nodeid=kwargs["nodeid"],
                    location=kwargs["location"],
                )
            else:
                raise ValueError(f"unknown event: {eventname}")
        except KeyboardInterrupt:
            # should not land in receiver-thread
            raise
        except:  # noqa
            from _pytest._code import ExceptionInfo

            excinfo = ExceptionInfo.from_current()
            print("!" * 20, excinfo)
            self.config.notify_exception(excinfo)
            self.shutdown()
            self.notify_inproc("errordown", node=self, error=excinfo)


def unserialize_warning_message(data):
    import warnings
    import importlib

    if data["message_module"]:
        mod = importlib.import_module(data["message_module"])
        cls = getattr(mod, data["message_class_name"])
        message = None
        if data["message_args"] is not None:
            try:
                message = cls(*data["message_args"])
            except TypeError:
                pass
        if message is None:
            # could not recreate the original warning instance;
            # create a generic Warning instance with the original
            # message at least
            message_text = "{mod}.{cls}: {msg}".format(
                mod=data["message_module"],
                cls=data["message_class_name"],
                msg=data["message_str"],
            )
            message = Warning(message_text)
    else:
        message = data["message_str"]

    if data["category_module"]:
        mod = importlib.import_module(data["category_module"])
        category = getattr(mod, data["category_class_name"])
    else:
        category = None

    kwargs = {"message": message, "category": category}
    # access private _WARNING_DETAILS because the attributes vary between Python versions
    for attr_name in warnings.WarningMessage._WARNING_DETAILS:  # type: ignore[attr-defined]
        if attr_name in ("message", "category"):
            continue
        kwargs[attr_name] = data[attr_name]

    return warnings.WarningMessage(**kwargs)  # type: ignore[arg-type]
