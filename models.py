# coding: utf-8
from sqlalchemy import ARRAY, Boolean, CHAR, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Table, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class PrismaMigration(Base):
    __tablename__ = '_prisma_migrations'

    id = Column(String(36), primary_key=True)
    checksum = Column(String(64), nullable=False)
    finished_at = Column(DateTime(True))
    migration_name = Column(String(255), nullable=False)
    logs = Column(Text)
    rolled_back_at = Column(DateTime(True))
    started_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    applied_steps_count = Column(Integer, nullable=False, server_default=text("0"))


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True, server_default=text("nextval('category_id_seq'::regclass)"))
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    image = Column(Text, nullable=False)
    slug = Column(Text, nullable=False, unique=True)
    parent_category_id = Column(ForeignKey('category.id', ondelete='SET NULL', onupdate='CASCADE'))

    parent_category = relationship('Category', remote_side=[id])
    products = relationship('Product', secondary='category_on_product')


class Country(Base):
    __tablename__ = 'country'

    id = Column(Integer, primary_key=True, server_default=text("nextval('country_id_seq'::regclass)"))
    code = Column(CHAR(2), nullable=False, unique=True)
    name = Column(Text, nullable=False)
    currency = Column(CHAR(3), nullable=False)


class Domain(Base):
    __tablename__ = 'domain'

    id = Column(Integer, primary_key=True, server_default=text("nextval('domain_id_seq'::regclass)"))
    name = Column(Text, nullable=False, unique=True)
    created_at = Column(TIMESTAMP(precision=3), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    valid_until = Column(TIMESTAMP(precision=3), nullable=False)


class IWantToBeNotified(Base):
    __tablename__ = 'i_want_to_be_notified'

    id = Column(Integer, primary_key=True, server_default=text("nextval('i_want_to_be_notified_id_seq'::regclass)"))
    email = Column(Text, nullable=False, unique=True)
    created_at = Column(TIMESTAMP(precision=3), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    notified = Column(Boolean, nullable=False, server_default=text("false"))


class Product(Base):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True, server_default=text("nextval('product_id_seq'::regclass)"))
    slug = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    subtitle = Column(Text)
    description = Column(Text, nullable=False)
    image = Column(Text, nullable=False)
    alt = Column(Text, nullable=False)
    seo_title = Column(Text, nullable=False)
    seo_description = Column(Text, nullable=False)
    requires_shipping = Column(Boolean, nullable=False, server_default=text("true"))
    is_digital_deliverable = Column(Boolean, nullable=False, server_default=text("false"))
    activation_type = Column(Enum('FAMILY_SPOT', 'INDIVIDUAL_PREMIUM', 'FAMILY_SPOT_RENEWAL', 'INDIVIDUAL_PREMIUM_RENEWAL', 'NONE', 'FAMILY_SPOT_CHEAPERSHOP', 'FAMILY_SPOT_TRIAL', name='ActivationType'))


class Profile(Base):
    __tablename__ = 'profile'

    id = Column(Text, primary_key=True)
    email = Column(Text, nullable=False, unique=True)
    name = Column(Text)
    avatar_url = Column(Text)
    stripe_customer_id = Column(Text)


class SpotifyFamilyAccount(Base):
    __tablename__ = 'spotify_family_account'

    id = Column(Integer, primary_key=True, server_default=text("nextval('spotify_family_account_id_seq'::regclass)"))
    home_id = Column(Text, unique=True)
    username = Column(Text, nullable=False, unique=True)
    display_name = Column(Text)
    email = Column(Text, nullable=False, unique=True)
    password = Column(Text, nullable=False)
    invite_link = Column(Text, nullable=False)
    physical_address = Column(Text, nullable=False)
    premium_start_date = Column(TIMESTAMP(precision=3))
    premium_end_date = Column(TIMESTAMP(precision=3))
    number_of_members = Column(Integer, nullable=False, server_default=text("0"))
    past_emails = Column(ARRAY(Text()))
    status = Column(Enum('CREATED', 'ACTIVE', 'INACTIVE', 'SUSPENDED', 'DEACTIVATED', name='FamilyAccountStatus'), nullable=False, server_default=text("'CREATED'::\"FamilyAccountStatus\""))


t_category_on_product = Table(
    'category_on_product', metadata,
    Column('product_id', ForeignKey('product.id', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('category_id', ForeignKey('category.id', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False)
)


class Customer(Base):
    __tablename__ = 'customer'

    id = Column(Integer, primary_key=True, server_default=text("nextval('customer_id_seq'::regclass)"))
    email = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    phone_number = Column(Text, nullable=False)
    date_of_birth = Column(TIMESTAMP(precision=3))
    country_code = Column(CHAR(2), nullable=False, server_default=text("'ES'::bpchar"))
    language_code = Column(CHAR(2), nullable=False, server_default=text("'es'::bpchar"))
    profile_id = Column(ForeignKey('profile.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False, unique=True)
    created_at = Column(TIMESTAMP(precision=3), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    profile = relationship('Profile')


class Discount(Base):
    __tablename__ = 'discount'

    id = Column(Integer, primary_key=True, server_default=text("nextval('discount_id_seq'::regclass)"))
    product_id = Column(ForeignKey('product.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    code = Column(Text, nullable=False)
    percentage = Column(Integer, nullable=False)
    start_date = Column(TIMESTAMP(precision=3), nullable=False)
    end_date = Column(TIMESTAMP(precision=3), nullable=False)

    product = relationship('Product')


class InternalFamilyPremiumUpgrade(Base):
    __tablename__ = 'internal_family_premium_upgrade'

    id = Column(Integer, primary_key=True, server_default=text("nextval('internal_family_premium_upgrade_id_seq'::regclass)"))
    spotify_family_account_id = Column(ForeignKey('spotify_family_account.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False, index=True)
    order_date = Column(TIMESTAMP(precision=3), nullable=False)
    payment_date = Column(TIMESTAMP(precision=3))
    status = Column(Enum('CREATED', 'PAID', 'COMPLETED', 'FAILED', name='PremiumOrderStatus'), nullable=False, server_default=text("'CREATED'::\"PremiumOrderStatus\""))
    payment_method = Column(Enum('BIZUM', 'STRIPE', 'CRYPTO', name='PremiumPaymentMethod'), nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(Text, nullable=False, server_default=text("'EUR'::text"))
    external_payment_id = Column(Text)
    notes = Column(Text)

    spotify_family_account = relationship('SpotifyFamilyAccount')


class ProductItem(Base):
    __tablename__ = 'product_item'

    id = Column(Integer, primary_key=True, server_default=text("nextval('product_item_id_seq'::regclass)"))
    sku = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    qty_in_stock = Column(Integer, nullable=False, server_default=text("0"))
    product_image = Column(Text)
    stripe_product_id = Column(Text)
    stripe_test_product_id = Column(Text)
    product_id = Column(ForeignKey('product.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    default_currency = Column(CHAR(3), nullable=False, server_default=text("'EUR'::bpchar"))
    default_price = Column(Integer, nullable=False)

    product = relationship('Product')
    variation_options = relationship('VariationOption', secondary='product_configuration')


class Review(Base):
    __tablename__ = 'review'

    id = Column(Integer, primary_key=True, server_default=text("nextval('review_id_seq'::regclass)"))
    name = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    date = Column(TIMESTAMP(precision=3), nullable=False)
    product_id = Column(ForeignKey('product.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)

    product = relationship('Product')


class Variation(Base):
    __tablename__ = 'variation'

    id = Column(Integer, primary_key=True, server_default=text("nextval('variation_id_seq'::regclass)"))
    slug = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    category_id = Column(ForeignKey('category.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)

    category = relationship('Category')


class ProductPrice(Base):
    __tablename__ = 'product_price'
    __table_args__ = (
        Index('product_price_product_item_id_country_id_key', 'product_item_id', 'country_id', unique=True),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('product_price_id_seq'::regclass)"))
    product_item_id = Column(ForeignKey('product_item.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    country_id = Column(ForeignKey('country.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    price = Column(Integer, nullable=False, server_default=text("0"))

    country = relationship('Country')
    product_item = relationship('ProductItem')


class SpotifyIndividualAccount(Base):
    __tablename__ = 'spotify_individual_account'

    id = Column(Integer, primary_key=True, server_default=text("nextval('spotify_individual_account_id_seq'::regclass)"))
    username = Column(Text, nullable=False, unique=True)
    password = Column(Text, nullable=False)
    email = Column(Text, nullable=False, unique=True)
    display_name = Column(Text)
    is_provided_by_service = Column(Boolean, nullable=False, server_default=text("false"))
    custom_email_domain = Column(Text)
    forwarded_contact_email = Column(Text)
    customer_id = Column(ForeignKey('customer.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)

    customer = relationship('Customer')


class VariationOption(Base):
    __tablename__ = 'variation_option'

    id = Column(Integer, primary_key=True, server_default=text("nextval('variation_option_id_seq'::regclass)"))
    slug = Column(Text, nullable=False, unique=True)
    value = Column(Text, nullable=False)
    variation_id = Column(ForeignKey('variation.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)

    variation = relationship('Variation')


t_product_configuration = Table(
    'product_configuration', metadata,
    Column('product_item_id', ForeignKey('product_item.id', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('variation_option_id', ForeignKey('variation_option.id', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False)
)


class SpotifyIndividualPremiumUpgrade(Base):
    __tablename__ = 'spotify_individual_premium_upgrade'

    id = Column(Integer, primary_key=True, server_default=text("nextval('spotify_individual_premium_upgrade_id_seq'::regclass)"))
    start_date = Column(TIMESTAMP(precision=3), nullable=False)
    end_date = Column(TIMESTAMP(precision=3), nullable=False)
    is_recurring = Column(Boolean, nullable=False)
    customer_id = Column(ForeignKey('customer.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    spotify_individual_account_id = Column(ForeignKey('spotify_individual_account.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    status = Column(Enum('CREATED', 'ACTIVE', 'INACTIVE', 'EXPIRED', 'CANCELLED', name='IndividualPremiumUpgradeStatus'), nullable=False, server_default=text("'CREATED'::\"IndividualPremiumUpgradeStatus\""))

    customer = relationship('Customer')
    spotify_individual_account = relationship('SpotifyIndividualAccount')


class ShopOrder(Base):
    __tablename__ = 'shop_order'

    id = Column(Integer, primary_key=True, server_default=text("nextval('shop_order_id_seq'::regclass)"))
    order_date = Column(TIMESTAMP(precision=3), nullable=False)
    status = Column(Enum('CREATED', 'PAID', 'CANCELLED', 'FULLFILLED', name='OrderStatus'), nullable=False)
    spotify_individual_premium_upgrade_id = Column(ForeignKey('spotify_individual_premium_upgrade.id', ondelete='SET NULL', onupdate='CASCADE'))
    total_amount = Column(Integer, nullable=False)
    currency = Column(Text, nullable=False, server_default=text("'EUR'::text"))
    shopify_order_id = Column(Text, unique=True)
    customer_id = Column(ForeignKey('customer.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)

    customer = relationship('Customer')
    spotify_individual_premium_upgrade = relationship('SpotifyIndividualPremiumUpgrade')


class OrderLine(Base):
    __tablename__ = 'order_line'

    id = Column(Integer, primary_key=True, server_default=text("nextval('order_line_id_seq'::regclass)"))
    order_id = Column(ForeignKey('shop_order.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_amount = Column(Integer, nullable=False)
    product_item_id = Column(ForeignKey('product_item.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)

    order = relationship('ShopOrder')
    product_item = relationship('ProductItem')


class Payment(Base):
    __tablename__ = 'payment'

    id = Column(Integer, primary_key=True, server_default=text("nextval('payment_id_seq'::regclass)"))
    payment_method = Column(Enum('BIZUM', 'STRIPE', name='PaymentMethod'), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(Enum('PENDING', 'PENDING_MANUAL_CONFIRMATION', 'COMPLETED', 'FAILED', 'CANCELLED', name='PaymentStatus'), nullable=False)
    payment_date = Column(TIMESTAMP(precision=3), nullable=False)
    is_recurring = Column(Boolean, nullable=False)
    external_payment_id = Column(Text)
    order_id = Column(ForeignKey('shop_order.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, unique=True)

    order = relationship('ShopOrder')


class SpotifyFamilySpotPeriod(Base):
    __tablename__ = 'spotify_family_spot_period'
    __table_args__ = (
        Index('idx_unique_active_spot', 'spotify_family_account_id', 'spot_number', unique=True),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('spotify_family_spot_period_id_seq'::regclass)"))
    start_date = Column(TIMESTAMP(precision=3), nullable=False)
    end_date = Column(TIMESTAMP(precision=3), nullable=False)
    trial_end_date = Column(TIMESTAMP(precision=3))
    spot_number = Column(Enum('ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', name='SpotNumber'), nullable=False)
    spotify_member_id = Column(Text, nullable=False)
    spotify_member_name = Column(Text)
    order_id = Column(ForeignKey('shop_order.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    customer_id = Column(ForeignKey('customer.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    spotify_account_id = Column(ForeignKey('spotify_individual_account.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    spotify_family_account_id = Column(ForeignKey('spotify_family_account.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    previous_period_id = Column(ForeignKey('spotify_family_spot_period.id', ondelete='SET NULL', onupdate='CASCADE'), unique=True)
    is_trial = Column(Boolean, nullable=False, server_default=text("false"))
    status = Column(Enum('ACTIVE', 'GRACE_PERIOD', 'EXPIRED', 'CANCELLED', 'ACTIVE_CHEAPERSHOP', name='SpotPeriodStatus'), nullable=False, server_default=text("'ACTIVE'::\"SpotPeriodStatus\""))
    payment_grace_period_end_date = Column(TIMESTAMP(precision=3))

    customer = relationship('Customer')
    order = relationship('ShopOrder')
    previous_period = relationship('SpotifyFamilySpotPeriod', remote_side=[id])
    spotify_account = relationship('SpotifyIndividualAccount')
    spotify_family_account = relationship('SpotifyFamilyAccount')


class ActivationKey(Base):
    __tablename__ = 'activation_key'

    key = Column(Text, nullable=False, unique=True)
    created_at = Column(TIMESTAMP(precision=3), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    used_at = Column(TIMESTAMP(precision=3))
    status = Column(Enum('CREATED', 'ACTIVE', 'REDEEMED', 'EXPIRED', 'REVOKED', 'SUSPENDED', 'IN_USE', name='ActivationKeyStatus'), nullable=False, server_default=text("'CREATED'::\"ActivationKeyStatus\""))
    order_line_id = Column(ForeignKey('order_line.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    product_item_id = Column(ForeignKey('product_item.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    activation_type = Column(Enum('FAMILY_SPOT', 'INDIVIDUAL_PREMIUM', 'FAMILY_SPOT_RENEWAL', 'INDIVIDUAL_PREMIUM_RENEWAL', 'NONE', 'FAMILY_SPOT_CHEAPERSHOP', 'FAMILY_SPOT_TRIAL', name='ActivationType'), nullable=False)
    spotify_family_spot_period_id = Column(ForeignKey('spotify_family_spot_period.id', ondelete='SET NULL', onupdate='CASCADE'), unique=True)
    spotify_individual_premium_upgrade_id = Column(ForeignKey('spotify_individual_premium_upgrade.id', ondelete='SET NULL', onupdate='CASCADE'), unique=True)
    id = Column(Integer, primary_key=True, server_default=text("nextval('activation_key_id_seq'::regclass)"))

    order_line = relationship('OrderLine')
    product_item = relationship('ProductItem')
    spotify_family_spot_period = relationship('SpotifyFamilySpotPeriod')
    spotify_individual_premium_upgrade = relationship('SpotifyIndividualPremiumUpgrade')


class DigitalDeliveryTask(Base):
    __tablename__ = 'digital_delivery_task'
    __table_args__ = (
        Index('digital_delivery_task_order_id_order_line_id_key', 'order_id', 'order_line_id', unique=True),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('digital_delivery_task_id_seq'::regclass)"))
    order_id = Column(ForeignKey('shop_order.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    order_line_id = Column(ForeignKey('order_line.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    created_at = Column(TIMESTAMP(precision=3), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    processed_at = Column(TIMESTAMP(precision=3))
    status = Column(Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='DeliveryStatus'), nullable=False, server_default=text("'PENDING'::\"DeliveryStatus\""))

    order = relationship('ShopOrder')
    order_line = relationship('OrderLine')


class SpotPeriodRenewal(Base):
    __tablename__ = 'spot_period_renewal'
    __table_args__ = (
        Index('spot_period_renewal_original_period_id_new_period_id_key', 'original_period_id', 'new_period_id', unique=True),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('spot_period_renewal_id_seq'::regclass)"))
    renewal_date = Column(TIMESTAMP(precision=3), nullable=False)
    status = Column(Enum('PENDING', 'COMPLETED', 'FAILED', name='RenewalStatus'), nullable=False)
    type = Column(Enum('MANUAL', 'AUTOMATIC', name='RenewalType'), nullable=False)
    recurring_payment_id = Column(Text)
    original_period_id = Column(ForeignKey('spotify_family_spot_period.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False, unique=True)
    new_period_id = Column(ForeignKey('spotify_family_spot_period.id', ondelete='SET NULL', onupdate='CASCADE'), unique=True)
    renewal_order_id = Column(ForeignKey('shop_order.id', ondelete='SET NULL', onupdate='CASCADE'))

    new_period = relationship('SpotifyFamilySpotPeriod', primaryjoin='SpotPeriodRenewal.new_period_id == SpotifyFamilySpotPeriod.id')
    original_period = relationship('SpotifyFamilySpotPeriod', primaryjoin='SpotPeriodRenewal.original_period_id == SpotifyFamilySpotPeriod.id')
    renewal_order = relationship('ShopOrder')


class Task(Base):
    __tablename__ = 'task'

    id = Column(Text, primary_key=True)
    type = Column(Enum('JOIN_FAMILY', 'RETRIEVE_FAMILY_DATA', 'HANDLE_SPOT_PERIOD_EXPIRATION', 'EMAIL_UPDATE', 'GET_FAMILY_RAW_MEMBERSHIPS', 'DELETE_MEMBER', name='TaskType'), nullable=False)
    status = Column(Enum('INITIATED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'SOLVING_CHALLENGE', 'FETCHING_CODE', 'CODE_RECEIVED', 'WAITING_FOR_CODE', 'ENTERING_CODE', 'SUBMITTING_CODE', 'CODE_SUBMITTED', 'INITIALIZING', 'LOGGING_IN', 'LOGGED_IN', 'SOLVING_CAPTCHA', 'NAVIGATING', 'EXTRACTING_USERNAME', 'USERNAME_EXTRACTED', 'EXTRACTING_DISPLAY_NAME', 'UPDATING_PROFILE', 'JOINING_FAMILY', 'CHECKING_ELIGIBILITY', 'ENTERING_ADDRESS', 'CONFIRMING', 'WRONG_PASSWORD', 'CAPTCHA_FAILED', 'ALREADY_PREMIUM', 'LIMIT_12', 'ERROR', 'TIMEOUT', 'LINK_EXPIRED', name='TaskStatus'), nullable=False)
    created_at = Column(TIMESTAMP(precision=3), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP(precision=3), nullable=False)
    customer_id = Column(ForeignKey('customer.id', ondelete='SET NULL', onupdate='CASCADE'))
    data = Column(JSONB(astext_type=Text()))
    error = Column(Text)
    step_description = Column(Text)
    spotify_family_accountId = Column(ForeignKey('spotify_family_account.id', ondelete='SET NULL', onupdate='CASCADE'))
    temp_code = Column(Text)
    used_ip_address = Column(Text)
    spotify_family_spot_periodId = Column(ForeignKey('spotify_family_spot_period.id', ondelete='SET NULL', onupdate='CASCADE'))

    customer = relationship('Customer')
    spotify_family_account = relationship('SpotifyFamilyAccount')
    spotify_family_spot_period = relationship('SpotifyFamilySpotPeriod')


class EmailUpdateTaskPayload(Base):
    __tablename__ = 'email_update_task_payload'

    id = Column(Text, primary_key=True)
    task_id = Column(ForeignKey('task.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, unique=True)
    old_email = Column(Text, nullable=False)
    new_email = Column(Text, nullable=False)

    task = relationship('Task')


class FamilyUpdateTaskPayload(Base):
    __tablename__ = 'family_update_task_payload'

    id = Column(Text, primary_key=True)
    task_id = Column(ForeignKey('task.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, unique=True)
    username = Column(Text)
    display_name = Column(Text)
    physical_address = Column(Text)
    number_of_members = Column(Integer)
    invite_link = Column(Text)
    status = Column(Text)
    premium_end_date = Column(TIMESTAMP(precision=3))
    premium_start_date = Column(TIMESTAMP(precision=3))

    task = relationship('Task')
