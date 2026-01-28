from app.forms.auth_forms import LoginForm, RegistrationForm
from app.forms.item_forms import CategoryForm, ItemForm, ItemDetailForm
from app.forms.stock_forms import StockForm, StockTransactionForm
from app.forms.installation_forms import DistributionForm, InstallationForm
from app.forms.warehouse_forms import WarehouseForm, BuildingForm, UnitForm, UnitDetailForm
from app.forms.procurement_forms import (
    ProcurementRequestForm,
    GoodsReceiptForm,
    ProcurementCompleteForm
)
from app.forms.user_forms import UserForm, UserWarehouseAssignmentForm
from app.forms.asset_request_forms import AssetRequestForm, AssetVerificationForm
from app.forms.asset_loan_forms import (
    AssetLoanRequestForm,
    AssetLoanApproveForm,
    AssetLoanShipForm,
    AssetLoanReceiveForm,
    AssetLoanReturnRequestForm,
    AssetLoanReturnApproveForm,
    AssetLoanItemReturnVerifyForm,
    AssetLoanItemUploadProofForm,
    VenueLoanForm
)
from app.forms.asset_transfer_forms import AssetTransferForm

__all__ = [
    'LoginForm', 'RegistrationForm',
    'CategoryForm', 'ItemForm', 'ItemDetailForm',
    'StockForm', 'StockTransactionForm',
    'DistributionForm', 'InstallationForm',
    'WarehouseForm', 'BuildingForm', 'UnitForm', 'UnitDetailForm',
    'ProcurementRequestForm',
    'GoodsReceiptForm',
    'ProcurementCompleteForm',
    'UserForm',
    'UserWarehouseAssignmentForm',
    'AssetRequestForm',
    'AssetVerificationForm',
    'AssetLoanRequestForm',
    'AssetLoanApproveForm',
    'AssetLoanShipForm',
    'AssetLoanReceiveForm',
    'AssetLoanReturnRequestForm',
    'AssetLoanReturnApproveForm',
    'AssetLoanItemReturnVerifyForm',
    'AssetLoanItemUploadProofForm',
    'VenueLoanForm',
    'AssetTransferForm'
]
