# -*- coding: utf-8 -*-
from ai_insights import(get_ai_insights,
                        get_goal_ai_insight,
                        get_budget_ai_insight,
                        get_dashboard_ai_insight,
                        get_investment_ai_insight,
                        parse_what_if_question,
                        translate_announcement_text,
                    )
import os
import math
from flask import Flask, render_template, redirect, request, session, flash, send_file, jsonify
import csv
import hmac
import hashlib
import secrets
from functools import wraps
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from import_engine import read_statement, normalize_rows, infer_statement_balance
from currency_engine import convert_transaction, convert_amount
from financial_intelligence import build_intelligence, simulate_purchase
from io import BytesIO, StringIO
from werkzeug.security import generate_password_hash
from database import (
    get_transactions,
    delete_transaction,
    get_transaction,
    update_transaction,
    add_transaction as db_add_transaction,
    create_user,
    get_user_by_email,
    get_user_by_id,
    check_user_password,
    get_goals,
    add_goal,
    delete_goal,
    get_budgets,
    add_budget,
    delete_budget,
    update_goal,
    get_monthly_savings,
    update_budget,
    get_budget_spending,
    get_report_totals,
    get_monthly_report,
    get_expense_categories,
    get_expense_categories_by_period,
    get_connection,
    get_ai_financial_context,
    add_goal_savings,
    batch_add_transactions,
    find_existing_transaction_keys,
    list_financial_accounts,
    list_bank_connections,
    create_bank_connection,
    get_bank_connection,
    get_bank_connection_by_consent,
    update_bank_connection,
    import_external_transaction,
    upsert_financial_account,
    create_manual_financial_account,
    get_financial_account,
    touch_financial_account,
    get_financial_account_activity,
    find_duplicate_manual_financial_account, update_financial_account, delete_financial_account, assign_transaction_account, ensure_financial_account_balance_schema, create_transfer, get_or_create_physical_cash_account,
)

from investment_features import (
    ensure_investment_schema, get_profile, save_profile, model_allocation,
    add_investment, update_investment_price, delete_investment, portfolio_summary, portfolio_health,
    add_watchlist, delete_watchlist, get_watchlist, financial_investment_context, EXPLORER
)

from bank_integration import configured as setu_configured, create_consent, get_consent, create_session, get_session, parse_transactions, parse_accounts

from product_features import (
    ensure_feature_schema,
    get_user_settings,
    update_user_settings,
    change_user_password,
    delete_user_account,
    get_gamification,
    award_activity,
    get_alerts,
    get_latest_unread_announcement,
    get_user_announcements,
    get_unread_announcement_count,
    mark_alert_read,
    clear_user_announcement,
    clear_read_user_announcements,
    sync_financial_alerts,
    send_email_alert,
    send_transactional_email,
    create_password_reset_token,
    password_reset_token_is_valid,
    reset_password_with_token,
    premium_features,
    get_ai_usage,
    consume_ai_request,
    get_ai_limits,
    get_premium_status,
    mark_subscription_cancellation_requested,
    submit_support_message,
    COUNTRY_CURRENCIES,
    COUNTRIES,
    currency_for_country,
    get_pricing,
    ensure_monetization_schema,
    list_coupons,
    create_coupon,
    toggle_coupon,
    remember_subscription_coupon,
    redeem_subscription_coupon,
    get_user_id_for_subscription,
    get_razorpay_subscription_id,
)
from admin_features import (
    ensure_admin_schema, get_admin_identity, get_user_access_state, touch_last_login,
    admin_login_blocked, record_admin_login, audit, dashboard_metrics, recent_activity,
    list_users as admin_list_users, user_detail as admin_user_detail, set_account_status,
    set_user_premium, delete_managed_user, add_admin_note, feature_analytics,
    list_support_messages, create_announcement, list_announcements, get_announcement,
    update_announcement, delete_announcement, list_staff_accounts, search_staff_candidates,
    set_staff_role, system_health, record_payment_event, list_payment_events,
)
app = Flask(__name__)

SIGORA_LANGUAGES = {"en": "English", "ta": "தமிழ்", "hi": "हिन्दी"}
SIGORA_TRANSLATIONS = {
    "en": {
        "menu":"Menu","close":"Close","home":"Home","dashboard":"Dashboard","transactions":"Transactions","reports":"Reports","budgets":"Budgets","goals":"Goals","invest":"Invest","import":"Import","insights":"SIGORA AI","intelligence":"Intelligence","accounts":"Accounts","settings":"Settings","premium":"Premium","logout":"Logout","tutorial":"How SIGORA works","personal_finance":"Personal finance","money":"Money","plan":"Plan","intelligence_group":"Intelligence","invest_group":"Invest & research","tools":"Tools","language":"Language","live":"Live","privacy":"Privacy","terms":"Terms","disclaimer":"Financial Disclaimer","support":"Support",
        "welcome":"Welcome back","money_now":"Here’s what your money looks like right now.","total_balance":"Total balance","total_income":"Total income","total_expenses":"Total expenses","recorded_income":"Recorded income","recorded_spending":"Recorded spending","recorded_activity":"Total recorded activity","income_minus":"Income minus expenses",
        "next_title":"Know what happens next.","next_sub":"SIGORA turns your recorded money into a forward-looking view — without inventing numbers.","health_score":"Financial Health","month_forecast":"Month-end forecast","projected_spend":"Projected spending","projected_savings":"Projected savings","risk_signal":"Budget risks","open_intelligence":"Explore your financial future","not_enough":"Add more financial activity to unlock this signal.",
        "settings_title":"Settings","settings_sub":"Make SIGORA work the way you want.","language_title":"App language","language_sub":"Choose the language SIGORA uses for navigation and key financial experiences.","save_language":"Use this language"
    },
    "ta": {
        "menu":"மெனு","close":"மூடு","home":"முகப்பு","dashboard":"டாஷ்போர்டு","transactions":"பரிவர்த்தனைகள்","reports":"அறிக்கைகள்","budgets":"பட்ஜெட்டுகள்","goals":"இலக்குகள்","invest":"முதலீடு","import":"இறக்குமதி","insights":"SIGORA AI","intelligence":"நிதி நுண்ணறிவு","accounts":"கணக்குகள்","settings":"அமைப்புகள்","premium":"பிரீமியம்","logout":"வெளியேறு","tutorial":"SIGORA எப்படி செயல்படுகிறது","personal_finance":"தனிநபர் நிதி","money":"பணம்","plan":"திட்டம்","intelligence_group":"நுண்ணறிவு","invest_group":"முதலீடு & ஆய்வு","tools":"கருவிகள்","language":"மொழி","live":"நேரலை","privacy":"தனியுரிமை","terms":"விதிமுறைகள்","disclaimer":"நிதி மறுப்பு","support":"உதவி",
        "welcome":"மீண்டும் வரவேற்கிறோம்","money_now":"உங்கள் பணநிலை இப்போது எப்படி இருக்கிறது என்பதைப் பாருங்கள்.","total_balance":"மொத்த இருப்பு","total_income":"மொத்த வருமானம்","total_expenses":"மொத்த செலவுகள்","recorded_income":"பதிவான வருமானம்","recorded_spending":"பதிவான செலவு","recorded_activity":"மொத்த பதிவான செயல்பாடு","income_minus":"வருமானம் கழித்து செலவுகள்",
        "next_title":"அடுத்து என்ன நடக்கும் என்பதை அறியுங்கள்.","next_sub":"நீங்கள் பதிவு செய்த நிதித் தரவை SIGORA எதிர்கால பார்வையாக மாற்றுகிறது — எண்களை உருவாக்காமல்.","health_score":"நிதி ஆரோக்கியம்","month_forecast":"மாத இறுதி கணிப்பு","projected_spend":"கணிக்கப்பட்ட செலவு","projected_savings":"கணிக்கப்பட்ட சேமிப்பு","risk_signal":"பட்ஜெட் அபாயங்கள்","open_intelligence":"உங்கள் நிதி எதிர்காலத்தைப் பாருங்கள்","not_enough":"இந்த தகவலைப் பெற மேலும் நிதிச் செயல்பாட்டைச் சேர்க்கவும்.",
        "settings_title":"அமைப்புகள்","settings_sub":"SIGORA-வை உங்களுக்கு ஏற்றபடி அமைக்கவும்.","language_title":"செயலி மொழி","language_sub":"வழிசெலுத்தல் மற்றும் முக்கிய நிதி அனுபவங்களுக்கு SIGORA பயன்படுத்தும் மொழியைத் தேர்ந்தெடுக்கவும்.","save_language":"இந்த மொழியைப் பயன்படுத்து"
    },
    "hi": {
        "menu":"मेनू","close":"बंद करें","home":"होम","dashboard":"डैशबोर्ड","transactions":"लेन-देन","reports":"रिपोर्ट","budgets":"बजट","goals":"लक्ष्य","invest":"निवेश","import":"इम्पोर्ट","insights":"SIGORA AI","intelligence":"वित्तीय इंटेलिजेंस","accounts":"खाते","settings":"सेटिंग्स","premium":"प्रीमियम","logout":"लॉग आउट","tutorial":"SIGORA कैसे काम करता है","personal_finance":"पर्सनल फाइनेंस","money":"पैसा","plan":"योजना","intelligence_group":"इंटेलिजेंस","invest_group":"निवेश और रिसर्च","tools":"टूल्स","language":"भाषा","live":"लाइव","privacy":"प्राइवेसी","terms":"शर्तें","disclaimer":"वित्तीय अस्वीकरण","support":"सहायता",
        "welcome":"वापसी पर स्वागत है","money_now":"देखिए आपका पैसा अभी कैसा दिख रहा है।","total_balance":"कुल बैलेंस","total_income":"कुल आय","total_expenses":"कुल खर्च","recorded_income":"दर्ज आय","recorded_spending":"दर्ज खर्च","recorded_activity":"कुल दर्ज गतिविधि","income_minus":"आय में से खर्च घटाकर",
        "next_title":"जानिए आगे क्या होगा।","next_sub":"SIGORA आपके दर्ज वित्तीय डेटा को भविष्य की साफ तस्वीर में बदलता है — बिना आंकड़े गढ़े।","health_score":"वित्तीय स्वास्थ्य","month_forecast":"महीने के अंत का अनुमान","projected_spend":"अनुमानित खर्च","projected_savings":"अनुमानित बचत","risk_signal":"बजट जोखिम","open_intelligence":"अपना वित्तीय भविष्य देखें","not_enough":"यह संकेत पाने के लिए और वित्तीय गतिविधि जोड़ें।",
        "settings_title":"सेटिंग्स","settings_sub":"SIGORA को अपने हिसाब से सेट करें।","language_title":"ऐप की भाषा","language_sub":"नेविगेशन और मुख्य वित्तीय अनुभवों के लिए SIGORA की भाषा चुनें।","save_language":"इस भाषा का उपयोग करें"
    }
}

# Expanded product language pack. Brand names, user-entered text, market symbols and
# legal identifiers intentionally remain unchanged.
_SIGORA_MORE = {
"en": {"connected_finances":"CONNECTED FINANCES","accounts_sub":"Keep each money source organised. Add an account, then import almost any common bank statement into it.","import_statement":"Import statement","accounts_added":"Accounts","statement_ready":"Statement formats","credentials":"Bank credentials","never_requested":"Never requested","your_accounts":"YOUR ACCOUNTS","money_sources":"Your money sources","statement_account":"Statement account","updated":"Updated","not_yet":"Not yet","add_first_account":"Add your first account","add_first_account_sub":"No bank login needed. Add the account label, then import a statement.","add_account":"Add account","bank_name":"Bank / institution","account_nickname":"Account nickname","primary_savings":"Primary savings","account_type":"Account type","savings":"Savings","current_account":"Current","credit_card":"Credit card","wallet":"Wallet","currency":"Currency","last_four":"Last 4 digits (optional)","current_balance_optional":"Current balance (optional)","safe_by_design":"Safe by design","bank_privacy":"Statement accounts work without sharing internet-banking credentials. Automatic live sync will only be enabled through a consent-based provider when available.","no_credentials":"SIGORA never asks for your bank password, OTP, card PIN or UPI PIN.","smart_import":"SMART DATA IMPORT","bring_transactions":"Bring your transactions in.","import_sub":"Upload a machine-readable bank statement. SIGORA detects the layout and converts it into one consistent transaction format.","imported":"Imported","duplicates_skipped":"duplicates skipped","rows_attention":"rows need attention","upload_statement":"Upload statement","import_into":"Import into account","general_transactions":"General transactions (no account)","choose_file":"Choose a file","pdf_password":"PDF password (encrypted PDFs only)","analyze_again":"Analyze again","analyze_statement":"Analyze statement","password_not_saved":"The password unlocks this PDF for this request only and is never saved.","intelligent_import":"INTELLIGENT IMPORT","messy_work":"SIGORA does the messy work.","detect":"Detect","detect_desc":"Finds likely headers, dates, narration, debit/credit and amount fields across common bank exports.","normalize":"Normalize","normalize_desc":"Converts different statement layouts into SIGORA date, description, type, category, amount and currency fields.","protect":"Protect","protect_desc":"Validates rows and checks duplicates before saving anything.","import_preview":"IMPORT PREVIEW","transactions_ready":"transactions ready","found":"Usable transactions found","date":"Date","description":"Description","type":"Type","category":"Category","amount":"Amount","select_same_file":"Select the same statement again to confirm import","confirm_import":"Confirm & import","rows_review":"Rows to review"},
"ta": {"connected_finances":"இணைக்கப்பட்ட நிதி","accounts_sub":"ஒவ்வொரு பண மூலத்தையும் ஒழுங்காக வைத்திருங்கள். கணக்கைச் சேர்த்து, பொதுவான வங்கி அறிக்கையை அதில் இறக்குமதி செய்யுங்கள்.","import_statement":"வங்கி அறிக்கையை இறக்குமதி செய்","accounts_added":"கணக்குகள்","statement_ready":"ஆதரிக்கப்படும் வடிவங்கள்","credentials":"வங்கி உள்நுழைவு தகவல்","never_requested":"ஒருபோதும் கேட்காது","your_accounts":"உங்கள் கணக்குகள்","money_sources":"உங்கள் பண மூலங்கள்","statement_account":"அறிக்கை கணக்கு","updated":"புதுப்பிப்பு","not_yet":"இன்னும் இல்லை","add_first_account":"முதல் கணக்கைச் சேர்க்கவும்","add_first_account_sub":"வங்கி உள்நுழைவு தேவையில்லை. கணக்கைச் சேர்த்து அதன் அறிக்கையை இறக்குமதி செய்யுங்கள்.","add_account":"கணக்கைச் சேர்","bank_name":"வங்கி / நிறுவனம்","account_nickname":"கணக்கு பெயர்","primary_savings":"முதன்மை சேமிப்பு","account_type":"கணக்கு வகை","savings":"சேமிப்பு","current_account":"நடப்பு கணக்கு","credit_card":"கிரெடிட் கார்டு","wallet":"வாலெட்","currency":"நாணயம்","last_four":"கடைசி 4 இலக்கங்கள் (விருப்பம்)","current_balance_optional":"தற்போதைய இருப்பு (விருப்பம்)","safe_by_design":"பாதுகாப்பை மையமாகக் கொண்டது","bank_privacy":"இணைய வங்கி உள்நுழைவு தகவலை பகிராமல் அறிக்கை கணக்குகள் செயல்படும். அனுமதி அடிப்படையிலான சேவை கிடைக்கும் போது மட்டுமே தானியங்கி நேரடி ஒத்திசைவு இயக்கப்படும்.","no_credentials":"SIGORA உங்கள் வங்கி கடவுச்சொல், OTP, கார்டு PIN அல்லது UPI PIN-ஐ ஒருபோதும் கேட்காது.","smart_import":"ஸ்மார்ட் தரவு இறக்குமதி","bring_transactions":"உங்கள் பரிவர்த்தனைகளை கொண்டு வாருங்கள்.","import_sub":"கணினி வாசிக்கக்கூடிய வங்கி அறிக்கையை பதிவேற்றுங்கள். SIGORA அதன் அமைப்பை கண்டறிந்து ஒரே மாதிரியான பரிவர்த்தனை வடிவமாக மாற்றும்.","imported":"இறக்குமதி செய்யப்பட்டது","duplicates_skipped":"நகல்கள் தவிர்க்கப்பட்டன","rows_attention":"வரிகள் கவனம் தேவை","upload_statement":"அறிக்கையை பதிவேற்று","import_into":"இந்த கணக்கில் இறக்குமதி செய்","general_transactions":"பொது பரிவர்த்தனைகள் (கணக்கு இல்லை)","choose_file":"கோப்பைத் தேர்ந்தெடுக்கவும்","pdf_password":"PDF கடவுச்சொல் (குறியாக்கப்பட்ட PDF மட்டும்)","analyze_again":"மீண்டும் பகுப்பாய்வு செய்","analyze_statement":"அறிக்கையை பகுப்பாய்வு செய்","password_not_saved":"இந்த PDF-ஐ திறக்க மட்டுமே கடவுச்சொல் பயன்படுத்தப்படும்; சேமிக்கப்படாது.","intelligent_import":"நுண்ணறிவு இறக்குமதி","messy_work":"சிக்கலான வேலையை SIGORA செய்கிறது.","detect":"கண்டறி","detect_desc":"பொதுவான வங்கி ஏற்றுமதிகளில் தலைப்புகள், தேதிகள், விவரம், டெபிட்/கிரெடிட் மற்றும் தொகையை கண்டறிகிறது.","normalize":"ஒரே வடிவமாக்கு","normalize_desc":"வேறுபட்ட அறிக்கை வடிவங்களை SIGORA தேதி, விவரம், வகை, பிரிவு, தொகை மற்றும் நாணய புலங்களாக மாற்றுகிறது.","protect":"பாதுகாப்பு","protect_desc":"சேமிப்பதற்கு முன் வரிகளை சரிபார்த்து நகல்களை கண்டறிகிறது.","import_preview":"இறக்குமதி முன்னோட்டம்","transactions_ready":"பரிவர்த்தனைகள் தயார்","found":"பயன்படுத்தக்கூடிய பரிவர்த்தனைகள்","date":"தேதி","description":"விவரம்","type":"வகை","category":"பிரிவு","amount":"தொகை","select_same_file":"இறக்குமதியை உறுதிப்படுத்த அதே அறிக்கையை மீண்டும் தேர்ந்தெடுக்கவும்","confirm_import":"உறுதிசெய்து இறக்குமதி செய்","rows_review":"சரிபார்க்க வேண்டிய வரிகள்"},
"hi": {"connected_finances":"जुड़ा हुआ वित्त","accounts_sub":"हर पैसे के स्रोत को व्यवस्थित रखें। खाता जोड़ें और सामान्य बैंक स्टेटमेंट उसमें इम्पोर्ट करें।","import_statement":"बैंक स्टेटमेंट इम्पोर्ट करें","accounts_added":"खाते","statement_ready":"समर्थित फ़ॉर्मैट","credentials":"बैंक लॉगिन जानकारी","never_requested":"कभी नहीं मांगी जाती","your_accounts":"आपके खाते","money_sources":"आपके पैसे के स्रोत","statement_account":"स्टेटमेंट खाता","updated":"अपडेट","not_yet":"अभी नहीं","add_first_account":"अपना पहला खाता जोड़ें","add_first_account_sub":"बैंक लॉगिन की जरूरत नहीं। खाता जोड़ें और उसका स्टेटमेंट इम्पोर्ट करें।","add_account":"खाता जोड़ें","bank_name":"बैंक / संस्था","account_nickname":"खाते का नाम","primary_savings":"मुख्य बचत","account_type":"खाते का प्रकार","savings":"बचत","current_account":"करंट अकाउंट","credit_card":"क्रेडिट कार्ड","wallet":"वॉलेट","currency":"मुद्रा","last_four":"अंतिम 4 अंक (वैकल्पिक)","current_balance_optional":"मौजूदा बैलेंस (वैकल्पिक)","safe_by_design":"सुरक्षा को ध्यान में रखकर","bank_privacy":"स्टेटमेंट खाते इंटरनेट बैंकिंग लॉगिन साझा किए बिना काम करते हैं। सहमति-आधारित प्रदाता उपलब्ध होने पर ही ऑटोमैटिक लाइव सिंक चालू होगा।","no_credentials":"SIGORA कभी आपका बैंक पासवर्ड, OTP, कार्ड PIN या UPI PIN नहीं मांगता।","smart_import":"स्मार्ट डेटा इम्पोर्ट","bring_transactions":"अपने लेन-देन लेकर आएं।","import_sub":"मशीन-पठनीय बैंक स्टेटमेंट अपलोड करें। SIGORA उसका लेआउट पहचानकर एक समान ट्रांजैक्शन फ़ॉर्मैट में बदलता है।","imported":"इम्पोर्ट हुए","duplicates_skipped":"डुप्लिकेट छोड़े गए","rows_attention":"पंक्तियों पर ध्यान चाहिए","upload_statement":"स्टेटमेंट अपलोड करें","import_into":"इस खाते में इम्पोर्ट करें","general_transactions":"सामान्य लेन-देन (कोई खाता नहीं)","choose_file":"फ़ाइल चुनें","pdf_password":"PDF पासवर्ड (केवल एन्क्रिप्टेड PDF)","analyze_again":"फिर से विश्लेषण करें","analyze_statement":"स्टेटमेंट का विश्लेषण करें","password_not_saved":"पासवर्ड केवल इस PDF को खोलने के लिए इस्तेमाल होता है और सेव नहीं किया जाता।","intelligent_import":"इंटेलिजेंट इम्पोर्ट","messy_work":"मुश्किल काम SIGORA करता है।","detect":"पहचानें","detect_desc":"सामान्य बैंक एक्सपोर्ट में हेडर, तारीख, विवरण, डेबिट/क्रेडिट और राशि फ़ील्ड पहचानता है।","normalize":"एक समान बनाएं","normalize_desc":"अलग स्टेटमेंट लेआउट को SIGORA की तारीख, विवरण, प्रकार, श्रेणी, राशि और मुद्रा में बदलता है।","protect":"सुरक्षित करें","protect_desc":"कुछ भी सेव करने से पहले पंक्तियों को जांचता और डुप्लिकेट पहचानता है।","import_preview":"इम्पोर्ट प्रीव्यू","transactions_ready":"लेन-देन तैयार","found":"उपयोगी लेन-देन मिले","date":"तारीख","description":"विवरण","type":"प्रकार","category":"श्रेणी","amount":"राशि","select_same_file":"इम्पोर्ट की पुष्टि के लिए वही स्टेटमेंट फिर चुनें","confirm_import":"पुष्टि करके इम्पोर्ट करें","rows_review":"जांचने वाली पंक्तियां"}
}
for _lang, _items in _SIGORA_MORE.items():
    SIGORA_TRANSLATIONS[_lang].update(_items)

SIGORA_PHRASE_TRANSLATIONS = {
"ta": {
"Add transaction":"பரிவர்த்தனையைச் சேர்","Transactions":"பரிவர்த்தனைகள்","Reports":"அறிக்கைகள்","Budgets":"பட்ஜெட்டுகள்","Goals":"இலக்குகள்","Settings":"அமைப்புகள்","Premium":"பிரீமியம்","Income":"வருமானம்","Expense":"செலவு","Expenses":"செலவுகள்","Amount":"தொகை","Date":"தேதி","Description":"விவரம்","Category":"பிரிவு","Type":"வகை","Balance":"இருப்பு","Current":"தற்போது","Target":"இலக்கு","Save Changes":"மாற்றங்களைச் சேமி","Update":"புதுப்பி","Delete":"நீக்கு","Cancel":"ரத்து செய்","Close":"மூடு","Preview":"முன்னோட்டம்","Log in":"உள்நுழை","Log out":"வெளியேறு","Email":"மின்னஞ்சல்","Password":"கடவுச்சொல்","Your account":"உங்கள் கணக்கு","Your profile":"உங்கள் சுயவிவரம்","Notifications":"அறிவிப்புகள்","Financial alerts":"நிதி எச்சரிக்கைகள்","AI features":"AI அம்சங்கள்","AI usage":"AI பயன்பாடு","Change password":"கடவுச்சொல்லை மாற்று","Delete account":"கணக்கை நீக்கு","Privacy Policy":"தனியுரிமைக் கொள்கை","Terms of Service":"சேவை விதிமுறைகள்","Support":"உதவி","Bank accounts":"கணக்குகள்","Import transactions":"பரிவர்த்தனைகளை இறக்குமதி செய்","Financial Health Score":"நிதி ஆரோக்கிய மதிப்பெண்","Month-end forecast":"மாத இறுதி கணிப்பு","Projected savings":"கணிக்கப்பட்ட சேமிப்பு","Predictive risks":"முன்கணிப்பு அபாயங்கள்","What-if purchase simulator":"வாங்கினால் என்ன ஆகும் சிமுலேட்டர்","Calculate scenario":"நிகழ்வை கணக்கிடு","Monthly Budget":"மாத பட்ஜெட்","My Budgets":"என் பட்ஜெட்டுகள்","My Goals":"என் இலக்குகள்","Create a budget":"பட்ஜெட்டை உருவாக்கு","Create a goal":"இலக்கை உருவாக்கு","Goal Name":"இலக்கு பெயர்","Target Amount":"இலக்கு தொகை","Target Date":"இலக்கு தேதி","Recent transactions":"சமீபத்திய பரிவர்த்தனைகள்","Total Income":"மொத்த வருமானம்","Total Expenses":"மொத்த செலவுகள்","Net Savings":"நிகர சேமிப்பு","Top categories":"முக்கிய பிரிவுகள்","Apply filters":"வடிகட்டலை பயன்படுத்து","All categories":"அனைத்து பிரிவுகள்","All types":"அனைத்து வகைகள்","Export transactions":"பரிவர்த்தனைகளை ஏற்றுமதி செய்","Add holding":"முதலீட்டைச் சேர்","Your holdings":"உங்கள் முதலீடுகள்","Watchlist":"கவனிப்புப் பட்டியல்","Market data unavailable right now":"சந்தைத் தரவு தற்போது கிடைக்கவில்லை","Settings saved.":"அமைப்புகள் சேமிக்கப்பட்டன.","Nothing here yet":"இன்னும் எதுவும் இல்லை","Everything looks good":"எல்லாம் நன்றாக உள்ளது","Open Intelligence →":"நிதி நுண்ணறிவைத் திற →","View reports →":"அறிக்கைகளைப் பார் →","View transactions":"பரிவர்த்தனைகளைப் பார்","Add your first transaction →":"முதல் பரிவர்த்தனையைச் சேர் →"},
"hi": {
"Add transaction":"लेन-देन जोड़ें","Transactions":"लेन-देन","Reports":"रिपोर्ट","Budgets":"बजट","Goals":"लक्ष्य","Settings":"सेटिंग्स","Premium":"प्रीमियम","Income":"आय","Expense":"खर्च","Expenses":"खर्च","Amount":"राशि","Date":"तारीख","Description":"विवरण","Category":"श्रेणी","Type":"प्रकार","Balance":"बैलेंस","Current":"वर्तमान","Target":"लक्ष्य","Save Changes":"बदलाव सेव करें","Update":"अपडेट करें","Delete":"हटाएं","Cancel":"रद्द करें","Close":"बंद करें","Preview":"प्रीव्यू","Log in":"लॉग इन","Log out":"लॉग आउट","Email":"ईमेल","Password":"पासवर्ड","Your account":"आपका खाता","Your profile":"आपकी प्रोफ़ाइल","Notifications":"सूचनाएं","Financial alerts":"वित्तीय अलर्ट","AI features":"AI फीचर्स","AI usage":"AI उपयोग","Change password":"पासवर्ड बदलें","Delete account":"खाता हटाएं","Privacy Policy":"प्राइवेसी पॉलिसी","Terms of Service":"सेवा की शर्तें","Support":"सहायता","Bank accounts":"खाते","Import transactions":"लेन-देन इम्पोर्ट करें","Financial Health Score":"वित्तीय स्वास्थ्य स्कोर","Month-end forecast":"महीने के अंत का अनुमान","Projected savings":"अनुमानित बचत","Predictive risks":"अनुमानित जोखिम","What-if purchase simulator":"खरीद सिमुलेटर","Calculate scenario":"स्थिति की गणना करें","Monthly Budget":"मासिक बजट","My Budgets":"मेरे बजट","My Goals":"मेरे लक्ष्य","Create a budget":"बजट बनाएं","Create a goal":"लक्ष्य बनाएं","Goal Name":"लक्ष्य का नाम","Target Amount":"लक्ष्य राशि","Target Date":"लक्ष्य तारीख","Recent transactions":"हाल के लेन-देन","Total Income":"कुल आय","Total Expenses":"कुल खर्च","Net Savings":"शुद्ध बचत","Top categories":"मुख्य श्रेणियां","Apply filters":"फ़िल्टर लगाएं","All categories":"सभी श्रेणियां","All types":"सभी प्रकार","Export transactions":"लेन-देन एक्सपोर्ट करें","Add holding":"होल्डिंग जोड़ें","Your holdings":"आपकी होल्डिंग्स","Watchlist":"वॉचलिस्ट","Market data unavailable right now":"मार्केट डेटा अभी उपलब्ध नहीं है","Settings saved.":"सेटिंग्स सेव हो गईं।","Nothing here yet":"अभी यहां कुछ नहीं है","Everything looks good":"सब ठीक है","Open Intelligence →":"इंटेलिजेंस खोलें →","View reports →":"रिपोर्ट देखें →","View transactions":"लेन-देन देखें","Add your first transaction →":"पहला लेन-देन जोड़ें →"}
}


# Comprehensive UI phrase pack for the final multilingual experience. User-entered
# values, ticker symbols, currency codes and brand names are intentionally untouched.
_SIGORA_UI_PHRASES = {
"ta": {
"Add transaction":"பரிவர்த்தனையைச் சேர்","Record it once. Sigora handles the rest.":"ஒருமுறை பதிவு செய்யுங்கள். மீதியை SIGORA கவனிக்கும்.","Transaction type":"பரிவர்த்தனை வகை","Leave as Auto to let Sigora decide":"தானாக வகைப்படுத்த SIGORA-வை அனுமதிக்க Auto-வாக விடுங்கள்","Create a Budget":"பட்ஜெட்டை உருவாக்கு","Create a Goal":"இலக்கை உருவாக்கு","Create Budget →":"பட்ஜெட்டை உருவாக்கு →","Create Goal →":"இலக்கை உருவாக்கு →","Edit Budget":"பட்ஜெட்டைத் திருத்து","Edit Goal":"இலக்கைத் திருத்து","Edit Transaction":"பரிவர்த்தனையைத் திருத்து","Monthly Budget":"மாத பட்ஜெட்","Limit":"வரம்பு","Spent":"செலவிட்டது","Status":"நிலை","Goal Name":"இலக்கு பெயர்","Target Amount":"இலக்கு தொகை","Target Date":"இலக்கு தேதி","Add savings":"சேமிப்பைச் சேர்","Give your money a plan":"உங்கள் பணத்திற்கு ஒரு திட்டம் கொடுங்கள்","Give every category a limit, then let Sigora help you stay inside it.":"ஒவ்வொரு பிரிவிற்கும் வரம்பை அமைக்கவும்; அதற்குள் இருக்க SIGORA உதவும்.","Give yourself something concrete to work toward.":"அடைய வேண்டிய தெளிவான நிதி இலக்கை அமைக்கவும்.","No budgets yet.":"இன்னும் பட்ஜெட்டுகள் இல்லை.","No goals yet.":"இன்னும் இலக்குகள் இல்லை.","No matching transactions.":"பொருந்தும் பரிவர்த்தனைகள் இல்லை.","Add a transaction or clear your filters to see your money activity.":"உங்கள் பணச் செயல்பாட்டைப் பார்க்க பரிவர்த்தனையைச் சேர்க்கவும் அல்லது வடிகட்டிகளை நீக்கவும்.","Every rupee in one place. Search, filter, edit and take your data with you.":"ஒவ்வொரு ரூபாயும் ஒரே இடத்தில். தேடவும், வடிகட்டவும், திருத்தவும், தரவை எடுத்துச் செல்லவும்.","Search":"தேடு","All categories":"அனைத்து பிரிவுகள்","All types":"அனைத்து வகைகள்","Apply filters":"வடிகட்டிகளைப் பயன்படுத்து","Export transactions":"பரிவர்த்தனைகளை ஏற்றுமதி செய்","Download filtered data as CSV or Excel":"வடிகட்டிய தரவை CSV அல்லது Excel ஆகப் பதிவிறக்கு","Filtered total":"வடிகட்டிய மொத்தம்","Income vs Expenses":"வருமானம் மற்றும் செலவுகள்","Where Your Money Goes":"உங்கள் பணம் எங்கு செல்கிறது","Top categories":"முக்கிய செலவுப் பிரிவுகள்","Financial overview":"நிதி மேலோட்டம்","Financial snapshot":"நிதி சுருக்கம்","This Month":"இந்த மாதம்","Last Month":"கடந்த மாதம்","This Year":"இந்த ஆண்டு","Last 6 months":"கடந்த 6 மாதங்கள்","Monthly Analysis":"மாதாந்திர பகுப்பாய்வு","Continue to Monthly Analysis":"மாதாந்திர பகுப்பாய்வுக்கு தொடரவும்","Understand where your money is going.":"உங்கள் பணம் எங்கு செல்கிறது என்பதைப் புரிந்துகொள்ளுங்கள்.","Build a clearer picture of where your money goes.":"உங்கள் பணம் எங்கு செல்கிறது என்பதை தெளிவாகப் பாருங்கள்.","Your spending by category.":"பிரிவுகளின்படி உங்கள் செலவு.","Latest activity":"சமீபத்திய செயல்பாடு","View all →":"அனைத்தையும் பார் →","Everything at a glance.":"எல்லாம் ஒரே பார்வையில்.","Your money, your picture, your next move.":"உங்கள் பணம், உங்கள் நிலை, உங்கள் அடுத்த முடிவு.","Start tracking your money":"உங்கள் பணத்தை கண்காணிக்கத் தொடங்குங்கள்","Start tracking your transactions":"பரிவர்த்தனைகளை கண்காணிக்கத் தொடங்குங்கள்","Your financial picture starts here.":"உங்கள் நிதி நிலை இங்கிருந்து தொடங்குகிறது.","Add income and expense transactions.":"வருமானம் மற்றும் செலவு பரிவர்த்தனைகளைச் சேர்க்கவும்.","Financial Health Score unlocks with your data":"உங்கள் தரவு சேர்ந்ததும் நிதி ஆரோக்கிய மதிப்பெண் திறக்கும்","What drives your score.":"உங்கள் மதிப்பெண்ணை நிர்ணயிப்பவை.","Only signals backed by your recorded data are included. Missing budgets, goals or history are not assigned artificial neutral scores.":"நீங்கள் பதிவு செய்த தரவால் ஆதரிக்கப்படும் சிக்னல்கள் மட்டுமே சேர்க்கப்படும். இல்லாத பட்ஜெட், இலக்கு அல்லது வரலாற்றுக்கு செயற்கை மதிப்பெண் வழங்கப்படாது.","EARLY WARNING ENGINE":"முன்கூட்டிய எச்சரிக்கை இயந்திரம்","Intervene before the breach.":"வரம்பை மீறும் முன் நடவடிக்கை எடுக்கவும்.","Goal Intelligence":"இலக்கு நுண்ணறிவு","Spending & income forecasts":"செலவு மற்றும் வருமான முன்கணிப்புகள்","Advanced reports":"மேம்பட்ட அறிக்கைகள்","Advanced AI Insights":"மேம்பட்ட AI நுண்ணறிவுகள்","AVAILABLE IN PREMIUM":"பிரீமியத்தில் கிடைக்கும்","Unlock simulator":"சிமுலேட்டரைத் திற","Simulate →":"சிமுலேட் செய் →","Can I afford this decision?":"இந்த முடிவை நான் ஏற்க முடியுமா?","Starting amount":"தொடக்கத் தொகை","Monthly contribution":"மாதாந்திர பங்களிப்பு","Years":"ஆண்டுகள்","Assumed annual return %":"கருதப்பட்ட ஆண்டு வருமானம் %","Enter assumptions and calculate a scenario.":"கருதுகோள்களை உள்ளிட்டு ஒரு நிலையை கணக்கிடுங்கள்.","Change the assumptions yourself. Projections are mathematical illustrations, not forecasts or promised returns.":"கருதுகோள்களை நீங்களே மாற்றலாம். இவை கணித விளக்கங்கள் மட்டுமே; உறுதியான வருமானம் அல்ல.","Investments":"முதலீடுகள்","Your money, beyond spending.":"செலவுக்கு அப்பாற்பட்ட உங்கள் பணம்.","Track investments, understand risk and connect your portfolio to your complete financial picture.":"முதலீடுகளை கண்காணித்து, அபாயத்தைப் புரிந்து, உங்கள் முழு நிதி நிலையுடன் போர்ட்ஃபோலியோவை இணைக்கவும்.","Your holdings":"உங்கள் முதலீடுகள்","Add holding":"முதலீட்டைச் சேர்","Holding":"முதலீடு","Invested cost":"முதலீட்டு செலவு","Current tracked value":"தற்போதைய கண்காணிப்பு மதிப்பு","Gain / loss":"லாபம் / இழப்பு","No holdings yet. Add your first investment above.":"இன்னும் முதலீடுகள் இல்லை. மேலே உங்கள் முதல் முதலீட்டைச் சேர்க்கவும்.","Your watchlist is empty.":"உங்கள் கவனிப்புப் பட்டியல் காலியாக உள்ளது.","Find & add":"தேடி சேர்","View chart →":"வரைபடத்தைப் பார் →","Market data unavailable right now":"சந்தைத் தரவு தற்போது கிடைக்கவில்லை","INVESTOR PROFILE":"முதலீட்டாளர் சுயவிவரம்","Tell Sigora what kind of investor you are.":"நீங்கள் எந்த வகை முதலீட்டாளர் என்பதை SIGORA-க்கு தெரிவிக்கவும்.","Investment horizon":"முதலீட்டு காலம்","Comfort with volatility":"விலை ஏற்ற இறக்கத்தை ஏற்கும் அளவு","Emergency fund coverage (months)":"அவசர நிதி பாதுகாப்பு (மாதங்கள்)","Educational profiling only.":"கல்வி நோக்கத்திற்கான சுயவிவரம் மட்டும்.","Build my profile →":"என் சுயவிவரத்தை உருவாக்கு →","AI Insights":"AI நுண்ணறிவுகள்","Explain your money":"உங்கள் பணத்தை விளக்குங்கள்","Turn your transaction history into clear, practical financial signals.":"உங்கள் பரிவர்த்தனை வரலாற்றை தெளிவான, பயனுள்ள நிதிச் சிக்னல்களாக மாற்றுங்கள்.","Generate AI insight":"AI நுண்ணறிவை உருவாக்கு","Analyzing your spending...":"உங்கள் செலவை பகுப்பாய்வு செய்கிறது...","Loading your spending analysis...":"உங்கள் செலவு பகுப்பாய்வு ஏற்றப்படுகிறது...","Your latest analysis":"உங்கள் சமீபத்திய பகுப்பாய்வு","AI USAGE":"AI பயன்பாடு","analyses this month":"இந்த மாத பகுப்பாய்வுகள்","Settings saved.":"அமைப்புகள் சேமிக்கப்பட்டன.","Your profile":"உங்கள் சுயவிவரம்","Country":"நாடு","Currency":"நாணயம்","Notifications":"அறிவிப்புகள்","Financial alerts":"நிதி எச்சரிக்கைகள்","AI features":"AI அம்சங்கள்","Change password":"கடவுச்சொல்லை மாற்று","Current password":"தற்போதைய கடவுச்சொல்","New password":"புதிய கடவுச்சொல்","Confirm new password":"புதிய கடவுச்சொல்லை உறுதிப்படுத்து","Update password":"கடவுச்சொல்லைப் புதுப்பி","DANGER ZONE":"அபாய பகுதி","Delete my account":"என் கணக்கை நீக்கு","This permanently removes your account and all associated financial data.":"இது உங்கள் கணக்கையும் அதனுடன் தொடர்புடைய அனைத்து நிதித் தரவையும் நிரந்தரமாக நீக்கும்.","We're here to help.":"உதவ நாங்கள் இருக்கிறோம்.","Issue type":"பிரச்சினை வகை","General question":"பொதுக் கேள்வி","Bug report":"பிழை அறிக்கை","Account and data requests":"கணக்கு மற்றும் தரவு கோரிக்கைகள்","Message":"செய்தி","Send to Sigora":"SIGORA-க்கு அனுப்பு","Welcome back.":"மீண்டும் வரவேற்கிறோம்.","Create your Sigora.":"உங்கள் SIGORA கணக்கை உருவாக்குங்கள்.","Create Account":"கணக்கை உருவாக்கு","Already have an account?":"ஏற்கனவே கணக்கு உள்ளதா?","Don't have an account?":"கணக்கு இல்லையா?","Forgot password?":"கடவுச்சொல் மறந்துவிட்டதா?","ACCOUNT RECOVERY":"கணக்கு மீட்பு","Your email":"உங்கள் மின்னஞ்சல்","Send reset link":"மீட்டமைப்பு இணைப்பை அனுப்பு","Choose a new password.":"புதிய கடவுச்சொல்லைத் தேர்ந்தெடுக்கவும்.","Reset password":"கடவுச்சொல்லை மீட்டமை","Back to login":"உள்நுழைவுக்கு திரும்பு","Page not found.":"பக்கம் கிடைக்கவில்லை.","Something went wrong.":"ஏதோ தவறு ஏற்பட்டது.","Back home":"முகப்புக்கு திரும்பு","January":"ஜனவரி","February":"பிப்ரவரி","March":"மார்ச்","April":"ஏப்ரல்","May":"மே","June":"ஜூன்","July":"ஜூலை","August":"ஆகஸ்ட்","September":"செப்டம்பர்","October":"அக்டோபர்","November":"நவம்பர்","December":"டிசம்பர்","Income vs expenses":"வருமானம் மற்றும் செலவுகள்","Income minus expenses":"வருமானம் கழித்து செலவுகள்","Biggest expense category":"அதிக செலவுள்ள பிரிவு","Month":"மாதம்","Year":"ஆண்டு","Name":"பெயர்","Value":"மதிப்பு","Action":"செயல்","Edit":"திருத்து","Add context":"கூடுதல் விவரம்","Next →":"அடுத்து →","← Back":"← பின்செல்","Open →":"திற →","View insight":"நுண்ணறிவைப் பார்","Open insight":"நுண்ணறிவைத் திற","Everything looks good":"எல்லாம் நன்றாக உள்ளது","Nothing here yet":"இன்னும் எதுவும் இல்லை","No major financial alerts based on your current recorded activity.":"தற்போதைய பதிவுகளின் அடிப்படையில் பெரிய நிதி எச்சரிக்கைகள் இல்லை."},
"hi": {
"Add transaction":"लेन-देन जोड़ें","Record it once. Sigora handles the rest.":"एक बार दर्ज करें। बाकी SIGORA संभालता है।","Transaction type":"लेन-देन का प्रकार","Leave as Auto to let Sigora decide":"SIGORA को अपने-आप चुनने देने के लिए Auto रहने दें","Create a Budget":"बजट बनाएं","Create a Goal":"लक्ष्य बनाएं","Create Budget →":"बजट बनाएं →","Create Goal →":"लक्ष्य बनाएं →","Edit Budget":"बजट संपादित करें","Edit Goal":"लक्ष्य संपादित करें","Edit Transaction":"लेन-देन संपादित करें","Monthly Budget":"मासिक बजट","Limit":"सीमा","Spent":"खर्च","Status":"स्थिति","Goal Name":"लक्ष्य का नाम","Target Amount":"लक्ष्य राशि","Target Date":"लक्ष्य तारीख","Add savings":"बचत जोड़ें","Give your money a plan":"अपने पैसे को एक योजना दें","Give every category a limit, then let Sigora help you stay inside it.":"हर श्रेणी की सीमा तय करें और SIGORA को उसके भीतर रहने में मदद करने दें।","Give yourself something concrete to work toward.":"अपने लिए एक स्पष्ट वित्तीय लक्ष्य तय करें।","No budgets yet.":"अभी कोई बजट नहीं है।","No goals yet.":"अभी कोई लक्ष्य नहीं है।","No matching transactions.":"कोई मेल खाता लेन-देन नहीं मिला।","Add a transaction or clear your filters to see your money activity.":"अपनी वित्तीय गतिविधि देखने के लिए लेन-देन जोड़ें या फ़िल्टर हटाएं।","Every rupee in one place. Search, filter, edit and take your data with you.":"हर रुपया एक जगह। खोजें, फ़िल्टर करें, संपादित करें और अपना डेटा साथ रखें।","Search":"खोजें","All categories":"सभी श्रेणियां","All types":"सभी प्रकार","Apply filters":"फ़िल्टर लगाएं","Export transactions":"लेन-देन एक्सपोर्ट करें","Download filtered data as CSV or Excel":"फ़िल्टर किया डेटा CSV या Excel में डाउनलोड करें","Filtered total":"फ़िल्टर किया कुल","Income vs Expenses":"आय और खर्च","Where Your Money Goes":"आपका पैसा कहां जाता है","Top categories":"मुख्य खर्च श्रेणियां","Financial overview":"वित्तीय अवलोकन","Financial snapshot":"वित्तीय सारांश","This Month":"इस महीने","Last Month":"पिछले महीने","This Year":"इस वर्ष","Last 6 months":"पिछले 6 महीने","Monthly Analysis":"मासिक विश्लेषण","Continue to Monthly Analysis":"मासिक विश्लेषण जारी रखें","Understand where your money is going.":"समझें कि आपका पैसा कहां जा रहा है।","Build a clearer picture of where your money goes.":"अपने खर्च की साफ तस्वीर बनाएं।","Your spending by category.":"श्रेणी के अनुसार आपका खर्च।","Latest activity":"हाल की गतिविधि","View all →":"सभी देखें →","Everything at a glance.":"सब कुछ एक नज़र में।","Your money, your picture, your next move.":"आपका पैसा, आपकी तस्वीर, आपका अगला कदम।","Start tracking your money":"अपने पैसे को ट्रैक करना शुरू करें","Start tracking your transactions":"अपने लेन-देन ट्रैक करना शुरू करें","Your financial picture starts here.":"आपकी वित्तीय तस्वीर यहां से शुरू होती है।","Add income and expense transactions.":"आय और खर्च के लेन-देन जोड़ें।","Financial Health Score unlocks with your data":"डेटा जुड़ने पर वित्तीय स्वास्थ्य स्कोर खुलेगा","What drives your score.":"आपका स्कोर किन चीज़ों से बनता है।","Only signals backed by your recorded data are included. Missing budgets, goals or history are not assigned artificial neutral scores.":"केवल आपके दर्ज डेटा से समर्थित संकेत शामिल होते हैं। गायब बजट, लक्ष्य या इतिहास को कृत्रिम स्कोर नहीं दिया जाता।","EARLY WARNING ENGINE":"पूर्व चेतावनी इंजन","Intervene before the breach.":"सीमा पार होने से पहले कार्रवाई करें।","Goal Intelligence":"लक्ष्य इंटेलिजेंस","Spending & income forecasts":"खर्च और आय के अनुमान","Advanced reports":"उन्नत रिपोर्ट","Advanced AI Insights":"उन्नत AI इनसाइट्स","AVAILABLE IN PREMIUM":"प्रीमियम में उपलब्ध","Unlock simulator":"सिमुलेटर खोलें","Simulate →":"सिमुलेट करें →","Can I afford this decision?":"क्या मैं यह निर्णय वहन कर सकता हूं?","Starting amount":"शुरुआती राशि","Monthly contribution":"मासिक योगदान","Years":"वर्ष","Assumed annual return %":"मान्य वार्षिक रिटर्न %","Enter assumptions and calculate a scenario.":"मान्यताएं दर्ज करके स्थिति की गणना करें।","Change the assumptions yourself. Projections are mathematical illustrations, not forecasts or promised returns.":"मान्यताएं खुद बदलें। अनुमान केवल गणितीय उदाहरण हैं, गारंटीड रिटर्न नहीं।","Investments":"निवेश","Your money, beyond spending.":"खर्च से आगे आपका पैसा।","Track investments, understand risk and connect your portfolio to your complete financial picture.":"निवेश ट्रैक करें, जोखिम समझें और पोर्टफोलियो को अपनी पूरी वित्तीय तस्वीर से जोड़ें।","Your holdings":"आपकी होल्डिंग्स","Add holding":"होल्डिंग जोड़ें","Holding":"होल्डिंग","Invested cost":"निवेश लागत","Current tracked value":"मौजूदा ट्रैक मूल्य","Gain / loss":"लाभ / हानि","No holdings yet. Add your first investment above.":"अभी कोई होल्डिंग नहीं है। ऊपर अपना पहला निवेश जोड़ें।","Your watchlist is empty.":"आपकी वॉचलिस्ट खाली है।","Find & add":"खोजें और जोड़ें","View chart →":"चार्ट देखें →","Market data unavailable right now":"मार्केट डेटा अभी उपलब्ध नहीं है","INVESTOR PROFILE":"निवेशक प्रोफ़ाइल","Tell Sigora what kind of investor you are.":"SIGORA को बताएं कि आप किस तरह के निवेशक हैं।","Investment horizon":"निवेश अवधि","Comfort with volatility":"उतार-चढ़ाव सहने की क्षमता","Emergency fund coverage (months)":"आपातकालीन फंड कवरेज (महीने)","Educational profiling only.":"केवल शैक्षिक प्रोफ़ाइल।","Build my profile →":"मेरी प्रोफ़ाइल बनाएं →","AI Insights":"AI इनसाइट्स","Explain your money":"अपने पैसे को समझें","Turn your transaction history into clear, practical financial signals.":"अपने लेन-देन इतिहास को स्पष्ट और उपयोगी वित्तीय संकेतों में बदलें।","Generate AI insight":"AI इनसाइट बनाएं","Analyzing your spending...":"आपके खर्च का विश्लेषण हो रहा है...","Loading your spending analysis...":"आपका खर्च विश्लेषण लोड हो रहा है...","Your latest analysis":"आपका नवीनतम विश्लेषण","AI USAGE":"AI उपयोग","analyses this month":"इस महीने के विश्लेषण","Settings saved.":"सेटिंग्स सेव हो गईं।","Your profile":"आपकी प्रोफ़ाइल","Country":"देश","Currency":"मुद्रा","Notifications":"सूचनाएं","Financial alerts":"वित्तीय अलर्ट","AI features":"AI फीचर्स","Change password":"पासवर्ड बदलें","Current password":"मौजूदा पासवर्ड","New password":"नया पासवर्ड","Confirm new password":"नया पासवर्ड पुष्टि करें","Update password":"पासवर्ड अपडेट करें","DANGER ZONE":"खतरे का क्षेत्र","Delete my account":"मेरा खाता हटाएं","This permanently removes your account and all associated financial data.":"यह आपके खाते और उससे जुड़े सभी वित्तीय डेटा को स्थायी रूप से हटा देता है।","We're here to help.":"हम मदद के लिए यहां हैं।","Issue type":"समस्या का प्रकार","General question":"सामान्य प्रश्न","Bug report":"बग रिपोर्ट","Account and data requests":"खाता और डेटा अनुरोध","Message":"संदेश","Send to Sigora":"SIGORA को भेजें","Welcome back.":"वापसी पर स्वागत है।","Create your Sigora.":"अपना SIGORA खाता बनाएं।","Create Account":"खाता बनाएं","Already have an account?":"पहले से खाता है?","Don't have an account?":"खाता नहीं है?","Forgot password?":"पासवर्ड भूल गए?","ACCOUNT RECOVERY":"खाता रिकवरी","Your email":"आपका ईमेल","Send reset link":"रीसेट लिंक भेजें","Choose a new password.":"नया पासवर्ड चुनें।","Reset password":"पासवर्ड रीसेट करें","Back to login":"लॉगिन पर वापस जाएं","Page not found.":"पेज नहीं मिला।","Something went wrong.":"कुछ गलत हो गया।","Back home":"होम पर वापस जाएं","January":"जनवरी","February":"फरवरी","March":"मार्च","April":"अप्रैल","May":"मई","June":"जून","July":"जुलाई","August":"अगस्त","September":"सितंबर","October":"अक्टूबर","November":"नवंबर","December":"दिसंबर","Income vs expenses":"आय और खर्च","Income minus expenses":"आय में से खर्च घटाकर","Biggest expense category":"सबसे बड़ी खर्च श्रेणी","Month":"महीना","Year":"वर्ष","Name":"नाम","Value":"मूल्य","Action":"कार्रवाई","Edit":"संपादित करें","Add context":"जानकारी जोड़ें","Next →":"अगला →","← Back":"← वापस","Open →":"खोलें →","View insight":"इनसाइट देखें","Open insight":"इनसाइट खोलें","Everything looks good":"सब ठीक है","Nothing here yet":"अभी यहां कुछ नहीं है","No major financial alerts based on your current recorded activity.":"आपकी मौजूदा दर्ज गतिविधि के आधार पर कोई बड़ा वित्तीय अलर्ट नहीं है।"}
}
for _lang, _items in _SIGORA_UI_PHRASES.items():
    SIGORA_PHRASE_TRANSLATIONS[_lang].update(_items)

# Final reviewed product-language pass: core dashboard, settings, investing and account experience.
_FINAL_I18N = {
"ta": {
"bank_account":"வங்கி கணக்கு","all_accounts":"அனைத்து கணக்குகள்","current_balance":"தற்போதைய இருப்பு","money_in":"வரவு","money_out":"செலவு","account_activity":"கணக்கு செயல்பாடு","recent_transactions":"சமீபத்திய பரிவர்த்தனைகள்","date":"தேதி","description":"விவரம்","category":"பிரிவு","amount":"தொகை","no_account_transactions":"இந்தக் கணக்கில் இன்னும் பரிவர்த்தனைகள் இல்லை","import_to_account_help":"இந்தக் கணக்கின் அறிக்கையை இறக்குமதி செய்தால் பரிவர்த்தனைகள் இங்கே தானாக ஒழுங்குபடுத்தப்படும்.","spending":"செலவுகள்","top_categories":"முக்கிய செலவு பிரிவுகள்","not_enough_spending_data":"செலவு பகுப்பாய்வுக்கு இன்னும் போதுமான தரவு இல்லை.","statement_status":"அறிக்கை நிலை","account_data":"கணக்கு தரவு","account_data_help":"SIGORA இறக்குமதி செய்த பரிவர்த்தனைகளை இந்தக் கணக்குடன் இணைத்து அறிக்கைகள் மற்றும் நுண்ணறிவில் பயன்படுத்துகிறது.","last_updated":"கடைசியாக புதுப்பிக்கப்பட்டது","view_account":"கணக்கைப் பார்","transactions":"பரிவர்த்தனைகள்","savings":"சேமிப்பு","current":"நடப்பு","current_account":"நடப்பு கணக்கு","credit_card":"கிரெடிட் கார்டு","wallet":"வாலெட்","Other":"மற்றவை","Food":"உணவு","Transport":"போக்குவரத்து","Shopping":"ஷாப்பிங்","Housing":"வீடு","Bills":"பில்கள்","Income":"வருமானம்",
"CONTROL CENTRE":"கட்டுப்பாட்டு மையம்","ACCOUNT":"கணக்கு","ALERTS":"எச்சரிக்கைகள்","SECURITY":"பாதுகாப்பு","DATA":"தரவு","SUPPORT":"உதவி","Your profile":"உங்கள் சுயவிவரம்","Save profile":"சுயவிவரத்தை சேமி","Email alerts":"மின்னஞ்சல் எச்சரிக்கைகள்","Send alerts to your account email.":"உங்கள் கணக்கு மின்னஞ்சலுக்கு எச்சரிக்கைகளை அனுப்பு.","Budget alerts":"பட்ஜெட் எச்சரிக்கைகள்","Warn me when a budget reaches 80% or is exceeded.":"பட்ஜெட் 80% அடையும்போது அல்லது மீறும்போது எச்சரி.","Goal reminders":"இலக்கு நினைவூட்டல்கள்","Remind me about approaching goals and completions.":"நெருங்கும் இலக்குகள் மற்றும் நிறைவு குறித்து நினைவூட்டு.","AI alerts":"AI எச்சரிக்கைகள்","Save notification settings":"அறிவிப்பு அமைப்புகளை சேமி","Launch price":"அறிமுக விலை","Explore Premium →":"Premium-ஐ பார்க்க →","Your data":"உங்கள் தரவு","Import transactions":"பரிவர்த்தனைகளை இறக்குமதி செய்","CSV, Excel and PDF bank statements":"CSV, Excel மற்றும் PDF வங்கி அறிக்கைகள்","Log out":"வெளியேறு","End this session":"இந்த அமர்வை முடி","Questions or issues?":"கேள்விகள் அல்லது சிக்கல்கள்?","Your email":"உங்கள் மின்னஞ்சல்","Tell us what you need help with...":"உங்களுக்கு என்ன உதவி வேண்டும் என்பதை கூறுங்கள்...","SMS alerts":"SMS எச்சரிக்கைகள்","SMS notifications":"SMS அறிவிப்புகள்","Delete account":"கணக்கை நீக்கு",
"SIGORA INVEST":"SIGORA முதலீடு","Important:":"முக்கியம்:","START HERE":"இங்கே தொடங்கு","Build risk profile":"ஆபத்து சுயவிவரத்தை உருவாக்கு","Edit profile":"சுயவிவரத்தை திருத்து","AI portfolio insight":"AI போர்ட்ஃபோலியோ நுண்ணறிவு","Your profile":"உங்கள் சுயவிவரம்","Horizon":"கால அளவு","Emergency cover":"அவசர நிதி பாதுகாப்பு","Monthly plan":"மாதாந்திர திட்டம்","Tracked return":"கண்காணிக்கப்பட்ட வருமானம்","ATTENTION":"கவனம்","Precautionary signals":"முன்னெச்சரிக்கை சிக்னல்கள்","EDUCATIONAL MODEL":"கல்வி மாதிரி","PORTFOLIO TRACKER":"போர்ட்ஃபோலியோ கண்காணிப்பு","Investment name":"முதலீட்டு பெயர்","Symbol (optional)":"குறியீடு (விருப்பம்)","Sector (optional)":"துறை (விருப்பம்)","Quantity":"அளவு","Average cost":"சராசரி செலவு","Current price":"தற்போதைய விலை","Notes (optional)":"குறிப்புகள் (விருப்பம்)","+ Add holding":"+ முதலீட்டை சேர்","Type":"வகை","Qty":"அளவு","Avg cost":"சராசரி செலவு","Current":"தற்போது","Return":"வருமானம்","Update":"புதுப்பி","DIVERSIFICATION":"பல்வகைப்படுத்தல்","What you actually own":"நீங்கள் உண்மையில் வைத்திருப்பவை","INVESTMENT EXPLORER":"முதலீட்டு ஆய்வு","Learn before you choose":"தேர்வு செய்வதற்கு முன் அறிக","PROJECTION LAB":"கணிப்பு ஆய்வகம்","Explore long-term scenarios":"நீண்டகால சூழல்களை ஆராயுங்கள்","Calculate scenario":"சூழலை கணக்கிடு","WATCHLIST":"கவனிப்பு பட்டியல்","Research queue":"ஆய்வு பட்டியல்","Optional research note":"விருப்ப ஆய்வு குறிப்பு","Remove":"நீக்கு"
},
"hi": {
"bank_account":"बैंक खाता","all_accounts":"सभी खाते","current_balance":"मौजूदा बैलेंस","money_in":"पैसा आया","money_out":"पैसा गया","account_activity":"खाता गतिविधि","recent_transactions":"हाल के लेन-देन","date":"तारीख","description":"विवरण","category":"श्रेणी","amount":"राशि","no_account_transactions":"इस खाते में अभी कोई लेन-देन नहीं है","import_to_account_help":"इस खाते का स्टेटमेंट इम्पोर्ट करें; SIGORA लेन-देन को अपने-आप व्यवस्थित करेगा।","spending":"खर्च","top_categories":"मुख्य खर्च श्रेणियां","not_enough_spending_data":"खर्च विश्लेषण के लिए अभी पर्याप्त डेटा नहीं है।","statement_status":"स्टेटमेंट स्थिति","account_data":"खाता डेटा","account_data_help":"SIGORA इम्पोर्ट किए लेन-देन को इस खाते से जोड़कर रिपोर्ट और इंटेलिजेंस में उपयोग करता है।","last_updated":"अंतिम अपडेट","view_account":"खाता देखें","transactions":"लेन-देन","savings":"बचत","current":"चालू","current_account":"चालू खाता","credit_card":"क्रेडिट कार्ड","wallet":"वॉलेट","Other":"अन्य","Food":"खाना","Transport":"यातायात","Shopping":"खरीदारी","Housing":"आवास","Bills":"बिल","Income":"आय",
"CONTROL CENTRE":"कंट्रोल सेंटर","ACCOUNT":"खाता","ALERTS":"अलर्ट","SECURITY":"सुरक्षा","DATA":"डेटा","SUPPORT":"सहायता","Your profile":"आपकी प्रोफ़ाइल","Save profile":"प्रोफ़ाइल सेव करें","Email alerts":"ईमेल अलर्ट","Send alerts to your account email.":"आपके खाते के ईमेल पर अलर्ट भेजें।","Budget alerts":"बजट अलर्ट","Warn me when a budget reaches 80% or is exceeded.":"बजट 80% तक पहुंचने या सीमा पार करने पर चेतावनी दें।","Goal reminders":"लक्ष्य रिमाइंडर","Remind me about approaching goals and completions.":"नज़दीक आते और पूरे होते लक्ष्यों की याद दिलाएं।","AI alerts":"AI अलर्ट","Save notification settings":"नोटिफिकेशन सेटिंग्स सेव करें","Launch price":"लॉन्च कीमत","Explore Premium →":"Premium देखें →","Your data":"आपका डेटा","Import transactions":"लेन-देन इम्पोर्ट करें","CSV, Excel and PDF bank statements":"CSV, Excel और PDF बैंक स्टेटमेंट","Log out":"लॉग आउट","End this session":"यह सत्र समाप्त करें","Questions or issues?":"सवाल या समस्या?","Your email":"आपका ईमेल","Tell us what you need help with...":"बताएं कि आपको किस सहायता की जरूरत है...","SMS alerts":"SMS अलर्ट","SMS notifications":"SMS नोटिफिकेशन","Delete account":"खाता हटाएं",
"SIGORA INVEST":"SIGORA निवेश","Important:":"महत्वपूर्ण:","START HERE":"यहां शुरू करें","Build risk profile":"जोखिम प्रोफ़ाइल बनाएं","Edit profile":"प्रोफ़ाइल संपादित करें","AI portfolio insight":"AI पोर्टफोलियो इनसाइट","Horizon":"अवधि","Emergency cover":"आपातकालीन सुरक्षा","Monthly plan":"मासिक योजना","Tracked return":"ट्रैक किया रिटर्न","ATTENTION":"ध्यान दें","Precautionary signals":"सावधानी संकेत","EDUCATIONAL MODEL":"शैक्षिक मॉडल","PORTFOLIO TRACKER":"पोर्टफोलियो ट्रैकर","Investment name":"निवेश का नाम","Symbol (optional)":"सिंबल (वैकल्पिक)","Sector (optional)":"सेक्टर (वैकल्पिक)","Quantity":"मात्रा","Average cost":"औसत लागत","Current price":"मौजूदा कीमत","Notes (optional)":"नोट्स (वैकल्पिक)","+ Add holding":"+ होल्डिंग जोड़ें","Type":"प्रकार","Qty":"मात्रा","Avg cost":"औसत लागत","Current":"मौजूदा","Return":"रिटर्न","Update":"अपडेट","DIVERSIFICATION":"विविधीकरण","What you actually own":"आप वास्तव में क्या रखते हैं","INVESTMENT EXPLORER":"निवेश एक्सप्लोरर","Learn before you choose":"चुनने से पहले समझें","PROJECTION LAB":"प्रोजेक्शन लैब","Explore long-term scenarios":"लंबी अवधि के परिदृश्य देखें","Calculate scenario":"परिदृश्य गणना करें","WATCHLIST":"वॉचलिस्ट","Research queue":"रिसर्च सूची","Optional research note":"वैकल्पिक रिसर्च नोट","Remove":"हटाएं"
}}
for _lang,_items in _FINAL_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_TRANSLATIONS[_lang].update(_items)
    SIGORA_PHRASE_TRANSLATIONS[_lang].update(_items)

# Last-mile reviewed translations for goals, dashboard, settings, AI and account editing.
_LAST_MILE = {
"ta": {"FINANCIAL PLANNING":"நிதி திட்டமிடல்","My Goals":"என் இலக்குகள்","Turn plans into milestones — and celebrate when you get there.":"திட்டங்களை இலக்குகளாக மாற்றி, அடையும் ஒவ்வொரு முன்னேற்றத்தையும் கொண்டாடுங்கள்.","+ Add goal":"+ இலக்கைச் சேர்","Saved":"சேமித்தது","Target":"இலக்கு","Goal completed — you did it.":"இலக்கு நிறைவேறியது — நீங்கள் சாதித்துவிட்டீர்கள்.","Target date has passed. Update the plan to keep moving.":"இலக்கு தேதி கடந்துவிட்டது. தொடர்ந்து முன்னேற திட்டத்தைப் புதுப்பிக்கவும்.","Monthly needed":"மாதத்திற்கு தேவை","Recent average":"சமீபத்திய சராசரி","Likelihood":"சாத்தியம்","Goal intelligence":"இலக்கு நுண்ணறிவு","Generate goal insight":"இலக்கு நுண்ணறிவை உருவாக்கு","Amount saved":"சேமித்த தொகை","+ Add savings":"+ சேமிப்பைச் சேர்","Delete":"நீக்கு","Create a goal":"இலக்கை உருவாக்கு","Top category":"முக்கிய செலவு பிரிவு","Top Category":"முக்கிய செலவு பிரிவு","Things worth seeing":"கவனிக்க வேண்டியவை","SMART ALERTS":"ஸ்மார்ட் எச்சரிக்கைகள்","FINANCIAL MOMENTUM":"நிதி முன்னேற்றம்","AI Insights":"AI நுண்ணறிவுகள்","AI usage":"AI பயன்பாடு","analyses this month":"இந்த மாத பகுப்பாய்வுகள்","PERSONALIZED":"தனிப்பயன்","Your latest analysis":"உங்கள் சமீபத்திய பகுப்பாய்வு","Budget and goal alerts by text message.":"பட்ஜெட் மற்றும் இலக்கு எச்சரிக்கைகளை குறுஞ்செய்தியாகப் பெறுங்கள்.","SMS is intentionally disabled for now. You will not be charged for SMS.":"SMS தற்போது திட்டமிட்டு முடக்கப்பட்டுள்ளது. SMS-க்கு கட்டணம் வசூலிக்கப்படாது.","Edit account":"கணக்கைத் திருத்து","Delete account":"கணக்கை நீக்கு","Payment account":"பணம் பயன்படுத்திய கணக்கு","Cash / unassigned":"பணம் / ஒதுக்கப்படாதது","Choose the account this money moved through.":"இந்தப் பணம் எந்தக் கணக்கில் நடந்தது என்பதைத் தேர்ந்தெடுக்கவும்."},
"hi": {"FINANCIAL PLANNING":"वित्तीय योजना","My Goals":"मेरे लक्ष्य","Turn plans into milestones — and celebrate when you get there.":"योजनाओं को लक्ष्य बनाएं और हर प्रगति का जश्न मनाएं।","+ Add goal":"+ लक्ष्य जोड़ें","Saved":"बचाया","Target":"लक्ष्य","Goal completed — you did it.":"लक्ष्य पूरा हुआ — आपने कर दिखाया।","Target date has passed. Update the plan to keep moving.":"लक्ष्य की तारीख निकल गई है। आगे बढ़ने के लिए योजना अपडेट करें।","Monthly needed":"हर महीने आवश्यक","Recent average":"हाल का औसत","Likelihood":"संभावना","Goal intelligence":"लक्ष्य इंटेलिजेंस","Generate goal insight":"लक्ष्य इनसाइट बनाएं","Amount saved":"बचाई गई राशि","+ Add savings":"+ बचत जोड़ें","Delete":"हटाएं","Create a goal":"लक्ष्य बनाएं","Top category":"मुख्य खर्च श्रेणी","Top Category":"मुख्य खर्च श्रेणी","Things worth seeing":"ध्यान देने योग्य बातें","SMART ALERTS":"स्मार्ट अलर्ट","FINANCIAL MOMENTUM":"वित्तीय प्रगति","AI Insights":"AI इनसाइट्स","AI usage":"AI उपयोग","analyses this month":"इस महीने के विश्लेषण","PERSONALIZED":"व्यक्तिगत","Your latest analysis":"आपका नवीनतम विश्लेषण","Budget and goal alerts by text message.":"बजट और लक्ष्य अलर्ट टेक्स्ट संदेश से पाएं।","SMS is intentionally disabled for now. You will not be charged for SMS.":"SMS अभी जानबूझकर बंद है। SMS के लिए कोई शुल्क नहीं लगेगा।","Edit account":"खाता संपादित करें","Delete account":"खाता हटाएं","Payment account":"भुगतान खाता","Cash / unassigned":"नकद / बिना खाते के","Choose the account this money moved through.":"वह खाता चुनें जिससे यह पैसा आया या गया।"}}
for _lang,_items in _LAST_MILE.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_TRANSLATIONS[_lang].update(_items)
    SIGORA_PHRASE_TRANSLATIONS[_lang].update(_items)


# Final reviewed full-product language pass (2026-09-01).
# Brand names, user-entered data, currency codes, market symbols and provider names stay unchanged.
_ULTIMATE_I18N = {
"ta": {
"QUICK START · 6 STEPS":"விரைவு தொடக்கம் · 6 படிகள்","How Sigora works":"SIGORA எப்படி செயல்படுகிறது","From your first transaction to a clearer view of your money.":"உங்கள் முதல் பரிவர்த்தனையிலிருந்து உங்கள் பணத்தின் தெளிவான பார்வை வரை.","Track your money":"உங்கள் பணத்தை கண்காணிக்கவும்","Add transactions manually or import a statement. Sigora turns the activity you record into the foundation for your dashboard and reports.":"பரிவர்த்தனைகளை கைமுறையாகச் சேர்க்கவும் அல்லது வங்கி அறிக்கையை இறக்குமதி செய்யவும். நீங்கள் பதிவு செய்யும் செயல்பாட்டை SIGORA டாஷ்போர்டு மற்றும் அறிக்கைகளுக்கான அடிப்படையாக மாற்றுகிறது.","Transactions → Import → Dashboard":"பரிவர்த்தனைகள் → இறக்குமதி → டாஷ்போர்டு","Give your money a plan":"உங்கள் பணத்திற்கு ஒரு திட்டம் கொடுங்கள்","Create monthly budgets and savings goals, then keep them updated as your spending and progress change.":"மாதாந்திர பட்ஜெட்டுகள் மற்றும் சேமிப்பு இலக்குகளை உருவாக்கி, செலவும் முன்னேற்றமும் மாறும்போது அவற்றைப் புதுப்பிக்கவும்.","Budgets → Goals":"பட்ஜெட்டுகள் → இலக்குகள்","Understand the bigger picture":"முழுப் படத்தையும் புரிந்துகொள்ளுங்கள்","Reports, Financial Health Score, forecasts and budget-risk signals help connect everyday activity to longer-term patterns.":"அறிக்கைகள், நிதி ஆரோக்கிய மதிப்பெண், கணிப்புகள் மற்றும் பட்ஜெட் அபாயச் சிக்னல்கள் தினசரி செயல்பாட்டை நீண்டகால போக்குகளுடன் இணைக்க உதவுகின்றன.","Reports → Intelligence":"அறிக்கைகள் → நிதி நுண்ணறிவு","Research your investments":"உங்கள் முதலீடுகளை ஆய்வு செய்யுங்கள்","Track holdings, build a watchlist and open market charts with plain-language context. Market information is educational and may be delayed.":"முதலீடுகளை கண்காணித்து, கவனிப்புப் பட்டியலை உருவாக்கி, எளிய விளக்கத்துடன் சந்தை வரைபடங்களைப் பாருங்கள். சந்தைத் தகவல் கல்விக்கானது; தாமதமாக இருக்கலாம்.","Invest → Watchlist → Market charts":"முதலீடு → கவனிப்புப் பட்டியல் → சந்தை வரைபடங்கள்","Use SIGORA AI thoughtfully":"SIGORA AI-ஐ பொறுப்புடன் பயன்படுத்துங்கள்","Insights can explain patterns in the financial data you record. They are educational, can be imperfect, and are not personalized investment advice.":"நீங்கள் பதிவு செய்த நிதித் தரவிலுள்ள போக்குகளை நுண்ணறிவுகள் விளக்கலாம். அவை கல்விக்கானவை, பிழைகள் இருக்கலாம், தனிப்பயன் முதலீட்டு ஆலோசனை அல்ல.","Insights → Intelligence → What-if":"AI நுண்ணறிவு → நிதி நுண்ணறிவு → என்ன ஆகும்?","You stay in control":"கட்டுப்பாடு எப்போதும் உங்களிடமே","Manage your profile, alerts and account from Settings. Premium uses secure Razorpay checkout when available for your billing currency. Never share passwords, OTPs or banking credentials with Sigora support.":"அமைப்புகளில் உங்கள் சுயவிவரம், எச்சரிக்கைகள் மற்றும் கணக்கை நிர்வகிக்கவும். உங்கள் பில்லிங் நாணயத்திற்கு கிடைக்கும் போது Premium பாதுகாப்பான Razorpay கட்டணத்தைப் பயன்படுத்துகிறது. கடவுச்சொல், OTP அல்லது வங்கி உள்நுழைவு தகவலை SIGORA உதவியுடன் பகிர வேண்டாம்.","Settings → Premium → Support":"அமைப்புகள் → Premium → உதவி","← Back":"← பின்","Next →":"அடுத்து →","Got it ✓":"புரிந்தது ✓","of":"இல்",
"SIGORA PREMIUM":"SIGORA PREMIUM","Advanced intelligence for people who want more than basic tracking.":"அடிப்படை கண்காணிப்பை விட அதிகம் விரும்புவோருக்கான மேம்பட்ட நிதி நுண்ணறிவு.","Make Sigora think harder.":"SIGORA-வின் மேம்பட்ட நுண்ணறிவைத் திறக்கவும்.","Current Premium price · Secure recurring billing powered by Razorpay.":"தற்போதைய Premium விலை · Razorpay மூலம் பாதுகாப்பான தொடர்ச்சியான கட்டணம்.","FREE VS PREMIUM":"இலவசம் vs PREMIUM","Feature":"அம்சம்","Free":"இலவசம்","Limited":"வரம்புள்ளது","AI-powered analyses":"AI ஆதரித்த பகுப்பாய்வுகள்","Advanced AI Insights":"மேம்பட்ட AI நுண்ணறிவுகள்","Goal Intelligence":"இலக்கு நுண்ணறிவு","Predictive budget-risk engine":"முன்கணிப்பு பட்ஜெட் அபாய இயந்திரம்","Financial Health Score":"நிதி ஆரோக்கிய மதிப்பெண்","What-if purchase simulator":"வாங்குதல் என்ன-ஆகும் சிமுலேட்டர்","Spending & income forecasts":"செலவு மற்றும் வருமான கணிப்புகள்","Personalized recommendations":"தனிப்பயன் பரிந்துரைகள்","Advanced reports":"மேம்பட்ட அறிக்கைகள்","Gamification":"விளையாட்டுமயமான முன்னேற்றம்","Budget & goal tools":"பட்ஜெட் & இலக்கு கருவிகள்","LIVE FINANCIAL SIGNAL":"நேரடி நிதிச் சிக்னல்","Financial Health Score unlocks with your data":"உங்கள் தரவுடன் நிதி ஆரோக்கிய மதிப்பெண் திறக்கப்படும்","AI USAGE":"AI பயன்பாடு","analyses used this month":"இந்த மாதம் பயன்படுத்திய பகுப்பாய்வுகள்","Daily safety limit:":"தினசரி பாதுகாப்பு வரம்பு:","Premium is active.":"Premium செயல்பாட்டில் உள்ளது.","Ready when you are.":"நீங்கள் தயாரானதும் தொடங்கலாம்.","Your Premium AI allowance is active.":"உங்கள் Premium AI பயன்பாட்டு வரம்பு செயல்பாட்டில் உள்ளது.","Upgrade securely with Razorpay. Your Premium access activates after payment confirmation.":"Razorpay மூலம் பாதுகாப்பாக மேம்படுத்துங்கள். கட்டணம் உறுதிசெய்யப்பட்டதும் Premium செயல்படும்.","Cancellation scheduled":"ரத்து செய்ய திட்டமிடப்பட்டது","Cancel at billing-cycle end":"பில்லிங் சுழற்சி முடிவில் ரத்து செய்","Coupon code (optional)":"கூப்பன் குறியீடு (விருப்பம்)","Checkout coming soon":"கட்டண வசதி விரைவில்","Cancellation scheduled for the end of your current billing cycle.":"தற்போதைய பில்லிங் சுழற்சி முடிவில் ரத்து செய்ய திட்டமிடப்பட்டுள்ளது.","Payment verified. Premium will unlock automatically after Razorpay confirms the subscription.":"கட்டணம் சரிபார்க்கப்பட்டது. Razorpay சந்தாவை உறுதிசெய்ததும் Premium தானாக திறக்கப்படும்.","That coupon is invalid, expired, or already used.":"அந்த கூப்பன் செல்லாது, காலாவதியானது அல்லது ஏற்கனவே பயன்படுத்தப்பட்டது.","We could not cancel the subscription. Please try again.":"சந்தாவை ரத்து செய்ய முடியவில்லை. மீண்டும் முயற்சிக்கவும்.","We could not verify that payment. Premium was not activated.":"அந்த கட்டணத்தை சரிபார்க்க முடியவில்லை. Premium செயல்படுத்தப்படவில்லை.","We couldn't start checkout. No charge was made. Please try again later.":"கட்டண செயல்முறையைத் தொடங்க முடியவில்லை. எந்தத் தொகையும் வசூலிக்கப்படவில்லை. பின்னர் முயற்சிக்கவும்.","Razorpay could not start this subscription. No charge was made. Please try again shortly or contact support if it continues.":"Razorpay இந்த சந்தாவைத் தொடங்க முடியவில்லை. எந்தத் தொகையும் வசூலிக்கப்படவில்லை. சிறிது நேரத்தில் முயற்சிக்கவும் அல்லது சிக்கல் தொடர்ந்தால் உதவியைத் தொடர்புகொள்ளவும்.","SECURE CHECKOUT":"பாதுகாப்பான கட்டணம்","Finish your Premium upgrade.":"உங்கள் Premium மேம்பாட்டை நிறைவு செய்யுங்கள்.","You'll complete payment securely through Razorpay.":"Razorpay மூலம் பாதுகாப்பாக கட்டணத்தை நிறைவு செய்வீர்கள்.","Open secure checkout →":"பாதுகாப்பான கட்டணத்தைத் திறக்கவும் →",
"Financial overview":"நிதி மேலோட்டம்","Financial snapshot":"நிதி நிலை சுருக்கம்","Income vs expenses":"வருமானம் vs செலவுகள்","Last 6 months":"கடந்த 6 மாதங்கள்","Latest activity":"சமீபத்திய செயல்பாடு","MONEY FLOW":"பண ஓட்டம்","SPENDING":"செலவு","Biggest expense category":"அதிக செலவான பிரிவு","No expense categories yet.":"இன்னும் செலவு பிரிவுகள் இல்லை.","Start tracking your money":"உங்கள் பணத்தை கண்காணிக்கத் தொடங்குங்கள்","Your financial picture starts here.":"உங்கள் நிதிப் படம் இங்கே தொடங்குகிறது.","Your financial activity will appear here once you start recording transactions.":"பரிவர்த்தனைகளை பதிவு செய்யத் தொடங்கியதும் உங்கள் நிதிச் செயல்பாடு இங்கே தோன்றும்.","Start tracking your transactions":"பரிவர்த்தனைகளை கண்காணிக்கத் தொடங்குங்கள்","No major financial alerts based on your current recorded activity.":"தற்போது பதிவு செய்த செயல்பாட்டின் அடிப்படையில் முக்கிய நிதி எச்சரிக்கைகள் இல்லை.","Spending is getting high":"செலவு அதிகரித்து வருகிறது","Watch your spending":"உங்கள் செலவை கவனியுங்கள்","You're spending more than you earn":"வருமானத்தை விட அதிகமாக செலவிடுகிறீர்கள்","Your current spending is ahead of your income.":"தற்போதைய செலவு உங்கள் வருமானத்தை விட அதிகமாக உள்ளது.","Your finances are currently in a healthy position.":"உங்கள் நிதிநிலை தற்போது ஆரோக்கியமாக உள்ளது.","Recommended next step":"அடுத்த பரிந்துரைக்கப்பட்ட படி","Focus area":"கவனம் செலுத்த வேண்டியது","Reduce spending":"செலவை குறைக்கவும்","View all →":"அனைத்தையும் பார்க்க →","Open →":"திறக்க →","QUICK VIEW":"விரைவு பார்வை","INSIGHT":"நுண்ணறிவு","ACTIVITY":"செயல்பாடு",
"PREMIUM":"PREMIUM","DANGER ZONE":"அபாய பகுதி","Name":"பெயர்","Country":"நாடு","Currency":"நாணயம்","Current password":"தற்போதைய கடவுச்சொல்","New password":"புதிய கடவுச்சொல்","Confirm new password":"புதிய கடவுச்சொல்லை உறுதிசெய்","Update password":"கடவுச்சொல்லைப் புதுப்பி","Delete my account":"என் கணக்கை நீக்கு","This permanently removes your account and all associated financial data.":"இது உங்கள் கணக்கையும் அதனுடன் தொடர்புடைய அனைத்து நிதித் தரவையும் நிரந்தரமாக நீக்கும்.","Import / Export":"இறக்குமதி / ஏற்றுமதி","Download filtered data as CSV or Excel":"வடிகட்டிய தரவை CSV அல்லது Excel ஆகப் பதிவிறக்கு","Issue type":"சிக்கல் வகை","General question":"பொது கேள்வி","Bug report":"பிழை அறிக்கை","Payments":"கட்டணங்கள்","Message":"செய்தி","Send to Sigora":"SIGORA-க்கு அனுப்பு","Support request received. We'll follow up using the email you provided.":"உதவி கோரிக்கை பெறப்பட்டது. நீங்கள் வழங்கிய மின்னஞ்சல் மூலம் தொடர்புகொள்வோம்.","SMS":"SMS","AI / Insights":"AI / நுண்ணறிவு",
"Turn your transaction history into clear, practical financial signals.":"உங்கள் பரிவர்த்தனை வரலாற்றை தெளிவான, நடைமுறை நிதிச் சிக்னல்களாக மாற்றுங்கள்.","AVAILABLE IN PREMIUM":"PREMIUM-ல் கிடைக்கும்","Unlock with Premium →":"Premium மூலம் திறக்கவும் →","AI":"AI",
"Give yourself something concrete to work toward.":"நீங்கள் அடைய வேண்டிய தெளிவான இலக்கை அமைக்கவும்.","No goals yet.":"இன்னும் இலக்குகள் இல்லை.","Edit":"திருத்து","Open insight":"நுண்ணறிவைத் திற","✓ Goal completed — you did it.":"✓ இலக்கு நிறைவேறியது — நீங்கள் சாதித்தீர்கள்.","✦ Generate goal insight":"✦ இலக்கு நுண்ணறிவை உருவாக்கு","✦ Goal intelligence":"✦ இலக்கு நுண்ணறிவு",
"BUDGETS":"பட்ஜெட்டுகள்","SPENDING CONTROL":"செலவு கட்டுப்பாடு","Give every category a limit, then let Sigora help you stay inside it.":"ஒவ்வொரு பிரிவுக்கும் வரம்பை அமைத்து, அதற்குள் இருக்க SIGORA உதவட்டும்.","+ Add budget":"+ பட்ஜெட்டைச் சேர்","No budgets yet.":"இன்னும் பட்ஜெட்டுகள் இல்லை.","Create your first spending limit and start getting better signals from Sigora.":"முதல் செலவு வரம்பை உருவாக்கி SIGORA-விலிருந்து சிறந்த சிக்னல்களைப் பெறத் தொடங்குங்கள்.","Limit":"வரம்பு","Spent":"செலவிட்டது","ON TRACK":"சரியான பாதையில்","WATCH":"கவனிக்கவும்","View insight":"நுண்ணறிவைப் பார்","✦ Generate AI insight":"✦ AI நுண்ணறிவை உருவாக்கு","✦ Sigora AI":"✦ SIGORA AI","MONTH":"மாதம்",
"MONEY CONTROL":"பண கட்டுப்பாடு","Every rupee in one place. Search, filter, edit and take your data with you.":"ஒவ்வொரு ரூபாயும் ஒரே இடத்தில். தேடவும், வடிகட்டவும், திருத்தவும், உங்கள் தரவை எடுத்துச் செல்லவும்.","+ Add transaction":"+ பரிவர்த்தனையைச் சேர்","INCOME":"வருமானம்","EXPENSES":"செலவுகள்","BALANCE":"இருப்பு","Filtered total":"வடிகட்டிய மொத்தம்","Income minus expenses":"வருமானம் கழித்து செலவுகள்","No matching transactions.":"பொருந்தும் பரிவர்த்தனைகள் இல்லை.","Add a transaction or clear your filters to see your money activity.":"பரிவர்த்தனையைச் சேர்க்கவும் அல்லது உங்கள் பணச் செயல்பாட்டைப் பார்க்க வடிகட்டிகளை நீக்கவும்.","DATE":"தேதி","DETAILS":"விவரங்கள்","TYPE":"வகை","AMOUNT":"தொகை","ACTION":"செயல்","VISIBLE":"காணப்படும்","↥ Export":"↥ ஏற்றுமதி","MONEY MOVEMENT":"பண நகர்வு","Record it once. Sigora handles the rest.":"ஒருமுறை பதிவு செய்யுங்கள். மீதியை SIGORA கவனிக்கும்.","Transaction type":"பரிவர்த்தனை வகை","Leave as Auto to let Sigora decide":"SIGORA தீர்மானிக்க Auto ஆக விடுங்கள்","Edit Transaction":"பரிவர்த்தனையைத் திருத்து","Transaction Type":"பரிவர்த்தனை வகை",
"Understand where your money is going.":"உங்கள் பணம் எங்கு செல்கிறது என்பதைப் புரிந்துகொள்ளுங்கள்.","Where Your Money Goes":"உங்கள் பணம் எங்கு செல்கிறது","Your overall financial picture.":"உங்கள் முழுமையான நிதிப் படம்.","Your spending by category.":"பிரிவு வாரியான உங்கள் செலவு.","Monthly Analysis":"மாதாந்திர பகுப்பாய்வு","Month Focus":"மாத கவனம்","This Month":"இந்த மாதம்","Last Month":"கடந்த மாதம்","This Year":"இந்த ஆண்டு","Continue to Monthly Analysis":"மாதாந்திர பகுப்பாய்வுக்கு தொடரவும்","Click a month to explore it.":"ஆய்வு செய்ய ஒரு மாதத்தைத் தேர்ந்தெடுக்கவும்.","Loading your spending analysis...":"உங்கள் செலவு பகுப்பாய்வு ஏற்றப்படுகிறது...","Analyzing your spending...":"உங்கள் செலவு பகுப்பாய்வு செய்யப்படுகிறது...","💡 Spending Breakdown":"💡 செலவு பிரிவு","💡 Sigora":"💡 SIGORA","Month":"மாதம்",
"Know what happens next.":"அடுத்து என்ன நடக்கும் என்பதை அறியுங்கள்.","EXPLAINABLE SCORE":"விளக்கக்கூடிய மதிப்பெண்","Your score begins with real data.":"உண்மையான தரவிலிருந்து உங்கள் மதிப்பெண் தொடங்குகிறது.","What drives your score.":"உங்கள் மதிப்பெண்ணை நிர்ணயிப்பவை.","Score":"மதிப்பெண்","Signal":"சிக்னல்","Status":"நிலை","Projected":"கணிக்கப்பட்டது","EARLY WARNING ENGINE":"முன்கூட்டிய எச்சரிக்கை இயந்திரம்","Intervene before the breach.":"வரம்பை மீறும் முன் நடவடிக்கை எடுக்கவும்.","WHAT-IF SIMULATOR · PREMIUM":"என்ன-ஆகும் சிமுலேட்டர் · PREMIUM","Can I afford this decision?":"இந்த முடிவை நான் ஏற்க முடியுமா?","Model a planned purchase against your recorded savings and goals.":"திட்டமிட்ட வாங்குதலை உங்கள் பதிவு செய்த சேமிப்புகள் மற்றும் இலக்குகளுடன் ஒப்பிட்டு பாருங்கள்.","Simulate →":"சிமுலேட் செய் →","Unlock simulator":"சிமுலேட்டரைத் திற","HOW TO UNLOCK":"எப்படி திறப்பது","Add financial data first":"முதலில் நிதித் தரவைச் சேர்க்கவும்","Add income and expense transactions.":"வருமானம் மற்றும் செலவு பரிவர்த்தனைகளைச் சேர்க்கவும்.","Build history":"வரலாற்றை உருவாக்கவும்","More months unlock stronger stability signals.":"அதிக மாதத் தரவு வலுவான நிலைத்தன்மை சிக்னல்களைத் திறக்கும்.","Add context":"கூடுதல் சூழலைச் சேர்க்கவும்","Create budgets and track goal progress.":"பட்ஜெட்டுகளை உருவாக்கி இலக்கு முன்னேற்றத்தை கண்காணிக்கவும்.","Forecasts are estimates from recorded data, not guarantees or regulated financial advice.":"கணிப்புகள் பதிவு செய்த தரவிலிருந்து பெறப்பட்ட மதிப்பீடுகள்; உத்தரவாதமோ ஒழுங்குபடுத்தப்பட்ட நிதி ஆலோசனையோ அல்ல.","Only signals backed by your recorded data are included. Missing budgets, goals or history are not assigned artificial neutral scores.":"நீங்கள் பதிவு செய்த தரவு ஆதரிக்கும் சிக்னல்கள் மட்டுமே சேர்க்கப்படும். இல்லாத பட்ஜெட், இலக்கு அல்லது வரலாற்றுக்கு செயற்கை மதிப்பெண் வழங்கப்படாது.","Explainable signals calculated from your recorded finances — before AI turns them into advice.":"AI விளக்குவதற்கு முன், உங்கள் பதிவு செய்த நிதித் தரவிலிருந்து கணக்கிடப்பட்ட விளக்கக்கூடிய சிக்னல்கள்.",
"Your money, beyond spending.":"செலவைத் தாண்டிய உங்கள் பணம்.","Track investments, understand risk and connect your portfolio to your complete financial picture.":"முதலீடுகளை கண்காணித்து, அபாயத்தைப் புரிந்து, உங்கள் போர்ட்ஃபோலியோவை முழு நிதிப் படத்துடன் இணைக்கவும்.","Tell Sigora what kind of investor you are.":"நீங்கள் எந்த வகை முதலீட்டாளர் என்பதை SIGORA-க்கு தெரிவிக்கவும்.","Create investor profile →":"முதலீட்டாளர் சுயவிவரத்தை உருவாக்கு →","Current tracked value":"தற்போது கண்காணிக்கப்படும் மதிப்பு","Invested cost":"முதலீட்டு செலவு","Gain / loss":"லாபம் / இழப்பு","Holding":"முதலீடு","Value":"மதிப்பு","No holdings yet. Add your first investment above.":"இன்னும் முதலீடுகள் இல்லை. மேலே உங்கள் முதல் முதலீட்டைச் சேர்க்கவும்.","Find & add":"தேடி சேர்க்கவும்","Your watchlist is empty.":"உங்கள் கவனிப்புப் பட்டியல் காலியாக உள்ளது.","View chart →":"வரைபடத்தைப் பார் →","Monthly contribution":"மாதாந்திர பங்களிப்பு","Assumed annual return %":"கருதப்பட்ட ஆண்டு வருமானம் %","Years":"ஆண்டுகள்","Illustrative ending value":"உதாரண இறுதி மதிப்பு","Enter assumptions and calculate a scenario.":"கருதுகோள்களை உள்ளிட்டு ஒரு சூழலைக் கணக்கிடுங்கள்.","Calculate scenario":"சூழலைக் கணக்கிடு","Change the assumptions yourself. Projections are mathematical illustrations, not forecasts or promised returns.":"கருதுகோள்களை நீங்களே மாற்றுங்கள். கணிப்புகள் கணித உதாரணங்கள் மட்டுமே; உறுதியான வருமான வாக்குறுதி அல்ல.","These are asset-class examples, not personalized picks.":"இவை சொத்து வகை உதாரணங்கள்; தனிப்பயன் தேர்வுகள் அல்ல.","This is a generic illustration for learning — not a recommendation for your money.":"இது கற்றலுக்கான பொதுவான உதாரணம்; உங்கள் பணத்திற்கான பரிந்துரை அல்ல.","Sigora provides educational analytics, portfolio tracking and risk information. It does not provide personalized buy/sell recommendations, target returns or guarantees.":"SIGORA கல்வி பகுப்பாய்வு, போர்ட்ஃபோலியோ கண்காணிப்பு மற்றும் அபாயத் தகவலை வழங்குகிறது. தனிப்பயன் வாங்க/விற்க பரிந்துரை, இலக்கு வருமானம் அல்லது உத்தரவாதம் வழங்காது.","✦ AI portfolio insight":"✦ AI போர்ட்ஃபோலியோ நுண்ணறிவு","Portfolio insight":"போர்ட்ஃபோலியோ நுண்ணறிவு","AI analysis across your tracked investments and financial readiness.":"நீங்கள் கண்காணிக்கும் முதலீடுகள் மற்றும் நிதித் தயார்நிலையை அடிப்படையாகக் கொண்ட AI பகுப்பாய்வு.","No security recommendations.":"குறிப்பிட்ட பத்திர பரிந்துரைகள் இல்லை.","Sigora analyses diversification, risk and financial context without telling you what named investment to buy or sell.":"எந்த குறிப்பிட்ட முதலீட்டை வாங்க அல்லது விற்க வேண்டும் என்று கூறாமல், பன்முகப்படுத்தல், அபாயம் மற்றும் நிதிச் சூழலை SIGORA பகுப்பாய்வு செய்கிறது.","MARKET RESEARCH":"சந்தை ஆய்வு","Latest market price":"சமீபத்திய சந்தை விலை","Day range":"நாள் வரம்பு","52-week range":"52 வார வரம்பு","Historical chart temporarily unavailable":"வரலாற்று வரைபடம் தற்காலிகமாக கிடைக்கவில்லை","What does this mean?":"இதன் பொருள் என்ன?","Remember:":"நினைவில் கொள்ளுங்கள்:","This explains market data; it is not a recommendation to buy, sell or hold this security. Prices can be delayed or temporarily unavailable.":"இது சந்தைத் தரவை விளக்குகிறது; இந்த பத்திரத்தை வாங்க, விற்க அல்லது வைத்திருக்க பரிந்துரை அல்ல. விலைகள் தாமதமாகவோ தற்காலிகமாக கிடைக்காமலோ இருக்கலாம்.","Sigora will not draw a trend from incomplete market history. Try another period or check again later.":"முழுமையற்ற சந்தை வரலாற்றிலிருந்து SIGORA போக்கை உருவாக்காது. வேறு காலத்தை முயற்சிக்கவும் அல்லது பின்னர் பார்க்கவும்.","INVESTOR PROFILE":"முதலீட்டாளர் சுயவிவரம்","How do you want your money to behave?":"உங்கள் பணம் எப்படிச் செயல்பட வேண்டும் என்று விரும்புகிறீர்கள்?","Educational profiling only.":"கல்விக்கான சுயவிவரம் மட்டும்.","Investment horizon":"முதலீட்டு காலவரம்பு","Primary objective":"முக்கிய நோக்கம்","Comfort with volatility":"விலை ஏற்றத் தாழ்வை ஏற்கும் அளவு","Emergency fund coverage (months)":"அவசர நிதி பாதுகாப்பு (மாதங்கள்)","Planned monthly investment":"திட்டமிட்ட மாதாந்திர முதலீடு","If markets fell sharply":"சந்தை கடுமையாக வீழ்ந்தால்","Long-term growth":"நீண்டகால வளர்ச்சி","Income + stability":"வருமானம் + நிலைத்தன்மை","Preserve capital / lower volatility":"மூலதன பாதுகாப்பு / குறைந்த ஏற்றத் தாழ்வு","Low — stability matters most":"குறைவு — நிலைத்தன்மை முக்கியம்","Moderate — some fluctuations are okay":"மிதமானது — சில ஏற்றத் தாழ்வுகள் பரவாயில்லை","High — I accept large fluctuations":"அதிகம் — பெரிய ஏற்றத் தாழ்வுகளை ஏற்கிறேன்","I would likely reduce exposure":"முதலீட்டு அளவை குறைப்பேன்","I would usually wait and review":"பொதுவாக காத்திருந்து மதிப்பாய்வு செய்வேன்","I could tolerate adding more":"மேலும் சேர்ப்பதை ஏற்க முடியும்","Build my profile →":"என் சுயவிவரத்தை உருவாக்கு →","This does not recommend specific securities or guarantee returns.":"இது குறிப்பிட்ட பத்திரங்களை பரிந்துரைக்காது அல்லது வருமானத்தை உத்தரவாதம் செய்யாது.",
"Welcome back.":"மீண்டும் வரவேற்கிறோம்.","Your money, your picture, your next move.":"உங்கள் பணம், உங்கள் படம், உங்கள் அடுத்த முடிவு.","Log In":"உள்நுழை","Forgot password?":"கடவுச்சொல் மறந்துவிட்டதா?","Don't have an account?":"கணக்கு இல்லையா?","Create one":"ஒன்றை உருவாக்குங்கள்","Create your Sigora.":"உங்கள் SIGORA கணக்கை உருவாக்குங்கள்.","Build a clearer picture of where your money goes.":"உங்கள் பணம் எங்கு செல்கிறது என்பதை தெளிவாகப் பாருங்கள்.","Create Account":"கணக்கை உருவாக்கு","Already have an account?":"ஏற்கனவே கணக்கு உள்ளதா?","START FRESH":"புதியதாக தொடங்குங்கள்","ACCOUNT RECOVERY":"கணக்கு மீட்பு","Reset your password.":"உங்கள் கடவுச்சொல்லை மீட்டமைக்கவும்.","Enter the email linked to your Sigora account. We'll send a secure, single-use reset link that expires in 30 minutes.":"உங்கள் SIGORA கணக்குடன் இணைந்த மின்னஞ்சலை உள்ளிடுங்கள். 30 நிமிடங்களில் காலாவதியாகும் பாதுகாப்பான ஒருமுறை பயன்பாட்டு இணைப்பை அனுப்புவோம்.","Send reset link":"மீட்டமைப்பு இணைப்பை அனுப்பு","← Back to login":"← உள்நுழைவுக்கு திரும்பு","Choose a new password.":"புதிய கடவுச்சொல்லைத் தேர்ந்தெடுக்கவும்.","Request a new link":"புதிய இணைப்பைக் கோருங்கள்","This reset link is invalid, expired, or has already been used.":"இந்த மீட்டமைப்பு இணைப்பு செல்லாது, காலாவதியானது அல்லது ஏற்கனவே பயன்படுத்தப்பட்டது.","Use at least 8 characters. Once saved, this reset link cannot be used again.":"குறைந்தது 8 எழுத்துகளைப் பயன்படுத்தவும். சேமித்த பிறகு இந்த இணைப்பை மீண்டும் பயன்படுத்த முடியாது.","We're here to help.":"உதவ நாங்கள் இருக்கிறோம்.","If something looks wrong, you find a bug, or you have a question about Sigora, contact us.":"ஏதேனும் தவறாகத் தோன்றினால், பிழை இருந்தால் அல்லது SIGORA பற்றி கேள்வி இருந்தால் எங்களைத் தொடர்புகொள்ளுங்கள்.","Account and data requests":"கணக்கு மற்றும் தரவு கோரிக்கைகள்","For account-specific help, email us from the address associated with your Sigora account when possible. Never send passwords, OTPs, card PINs, API keys, or full banking credentials.":"கணக்கு சார்ந்த உதவிக்கு முடிந்தால் SIGORA கணக்குடன் இணைந்த மின்னஞ்சலிலிருந்து எழுதுங்கள். கடவுச்சொல், OTP, கார்டு PIN, API key அல்லது முழு வங்கி உள்நுழைவு தகவலை ஒருபோதும் அனுப்ப வேண்டாம்.","You can manage many settings directly inside Sigora. Account deletion is available in Settings. If you cannot access your account or need help with a data request, email support.":"பல அமைப்புகளை SIGORA-வில் நேரடியாக நிர்வகிக்கலாம். கணக்கை நீக்கும் வசதி அமைப்புகளில் உள்ளது. கணக்கை அணுக முடியாவிட்டால் அல்லது தரவு கோரிக்கைக்கு உதவி தேவைப்பட்டால் உதவி மின்னஞ்சலைத் தொடர்புகொள்ளுங்கள்."
},
"hi": {
"QUICK START · 6 STEPS":"क्विक स्टार्ट · 6 चरण","How Sigora works":"SIGORA कैसे काम करता है","From your first transaction to a clearer view of your money.":"आपके पहले लेन-देन से आपके पैसे की साफ तस्वीर तक।","Track your money":"अपने पैसे को ट्रैक करें","Add transactions manually or import a statement. Sigora turns the activity you record into the foundation for your dashboard and reports.":"लेन-देन मैन्युअली जोड़ें या बैंक स्टेटमेंट इम्पोर्ट करें। आपकी दर्ज गतिविधि को SIGORA डैशबोर्ड और रिपोर्ट की नींव बनाता है।","Transactions → Import → Dashboard":"लेन-देन → इम्पोर्ट → डैशबोर्ड","Give your money a plan":"अपने पैसे को योजना दें","Create monthly budgets and savings goals, then keep them updated as your spending and progress change.":"मासिक बजट और बचत लक्ष्य बनाएं और खर्च व प्रगति बदलने पर उन्हें अपडेट रखें।","Budgets → Goals":"बजट → लक्ष्य","Understand the bigger picture":"पूरी तस्वीर समझें","Reports, Financial Health Score, forecasts and budget-risk signals help connect everyday activity to longer-term patterns.":"रिपोर्ट, वित्तीय स्वास्थ्य स्कोर, पूर्वानुमान और बजट-जोखिम संकेत रोज़मर्रा की गतिविधि को लंबे समय के पैटर्न से जोड़ते हैं।","Reports → Intelligence":"रिपोर्ट → वित्तीय इंटेलिजेंस","Research your investments":"अपने निवेश पर रिसर्च करें","Track holdings, build a watchlist and open market charts with plain-language context. Market information is educational and may be delayed.":"होल्डिंग ट्रैक करें, वॉचलिस्ट बनाएं और आसान भाषा के संदर्भ के साथ मार्केट चार्ट देखें। मार्केट जानकारी शैक्षिक है और देरी से मिल सकती है।","Invest → Watchlist → Market charts":"निवेश → वॉचलिस्ट → मार्केट चार्ट","Use SIGORA AI thoughtfully":"SIGORA AI का समझदारी से उपयोग करें","Insights can explain patterns in the financial data you record. They are educational, can be imperfect, and are not personalized investment advice.":"इनसाइट्स आपके दर्ज वित्तीय डेटा के पैटर्न समझा सकती हैं। वे शैक्षिक हैं, उनमें त्रुटि हो सकती है और वे व्यक्तिगत निवेश सलाह नहीं हैं।","Insights → Intelligence → What-if":"AI इनसाइट्स → इंटेलिजेंस → व्हाट-इफ","You stay in control":"नियंत्रण आपके पास रहता है","Manage your profile, alerts and account from Settings. Premium uses secure Razorpay checkout when available for your billing currency. Never share passwords, OTPs or banking credentials with Sigora support.":"सेटिंग्स से प्रोफ़ाइल, अलर्ट और खाता संभालें। आपकी बिलिंग मुद्रा में उपलब्ध होने पर Premium सुरक्षित Razorpay चेकआउट इस्तेमाल करता है। पासवर्ड, OTP या बैंक लॉगिन जानकारी SIGORA सपोर्ट से कभी साझा न करें।","Settings → Premium → Support":"सेटिंग्स → Premium → सहायता","← Back":"← वापस","Next →":"अगला →","Got it ✓":"समझ गया ✓","of":"में से",
"Advanced intelligence for people who want more than basic tracking.":"बेसिक ट्रैकिंग से आगे बढ़ने वालों के लिए उन्नत वित्तीय इंटेलिजेंस।","Make Sigora think harder.":"SIGORA की उन्नत इंटेलिजेंस अनलॉक करें।","Current Premium price · Secure recurring billing powered by Razorpay.":"मौजूदा Premium कीमत · Razorpay द्वारा सुरक्षित आवर्ती बिलिंग।","FREE VS PREMIUM":"फ्री बनाम PREMIUM","Feature":"फ़ीचर","Free":"फ्री","Limited":"सीमित","AI-powered analyses":"AI आधारित विश्लेषण","Advanced AI Insights":"उन्नत AI इनसाइट्स","Goal Intelligence":"लक्ष्य इंटेलिजेंस","Predictive budget-risk engine":"पूर्वानुमानित बजट-जोखिम इंजन","Financial Health Score":"वित्तीय स्वास्थ्य स्कोर","What-if purchase simulator":"खरीद व्हाट-इफ सिम्युलेटर","Spending & income forecasts":"खर्च और आय पूर्वानुमान","Personalized recommendations":"व्यक्तिगत सुझाव","Advanced reports":"उन्नत रिपोर्ट","Gamification":"गेमिफिकेशन","Budget & goal tools":"बजट और लक्ष्य टूल","LIVE FINANCIAL SIGNAL":"लाइव वित्तीय संकेत","Financial Health Score unlocks with your data":"आपके डेटा के साथ वित्तीय स्वास्थ्य स्कोर अनलॉक होगा","AI USAGE":"AI उपयोग","analyses used this month":"इस महीने उपयोग किए गए विश्लेषण","Daily safety limit:":"दैनिक सुरक्षा सीमा:","Premium is active.":"Premium सक्रिय है।","Ready when you are.":"आप तैयार हों तो शुरू करें।","Your Premium AI allowance is active.":"आपकी Premium AI सीमा सक्रिय है।","Upgrade securely with Razorpay. Your Premium access activates after payment confirmation.":"Razorpay से सुरक्षित अपग्रेड करें। भुगतान की पुष्टि के बाद Premium सक्रिय होगा।","Cancellation scheduled":"रद्द करना निर्धारित है","Cancel at billing-cycle end":"बिलिंग चक्र के अंत में रद्द करें","Coupon code (optional)":"कूपन कोड (वैकल्पिक)","Checkout coming soon":"चेकआउट जल्द उपलब्ध होगा","Cancellation scheduled for the end of your current billing cycle.":"मौजूदा बिलिंग चक्र के अंत में रद्द करना निर्धारित है।","Payment verified. Premium will unlock automatically after Razorpay confirms the subscription.":"भुगतान सत्यापित हुआ। Razorpay सदस्यता की पुष्टि के बाद Premium अपने आप अनलॉक होगा।","That coupon is invalid, expired, or already used.":"यह कूपन अमान्य, समाप्त या पहले उपयोग हो चुका है।","We could not cancel the subscription. Please try again.":"सदस्यता रद्द नहीं हो सकी। कृपया फिर कोशिश करें।","We could not verify that payment. Premium was not activated.":"भुगतान सत्यापित नहीं हो सका। Premium सक्रिय नहीं हुआ।","We couldn't start checkout. No charge was made. Please try again later.":"चेकआउट शुरू नहीं हो सका। कोई शुल्क नहीं लिया गया। बाद में फिर कोशिश करें।","Razorpay could not start this subscription. No charge was made. Please try again shortly or contact support if it continues.":"Razorpay सदस्यता शुरू नहीं कर सका। कोई शुल्क नहीं लिया गया। थोड़ी देर बाद कोशिश करें या समस्या जारी रहे तो सहायता से संपर्क करें।","SECURE CHECKOUT":"सुरक्षित चेकआउट","Finish your Premium upgrade.":"अपना Premium अपग्रेड पूरा करें।","You'll complete payment securely through Razorpay.":"आप Razorpay के माध्यम से सुरक्षित भुगतान पूरा करेंगे।","Open secure checkout →":"सुरक्षित चेकआउट खोलें →",
"Financial overview":"वित्तीय अवलोकन","Financial snapshot":"वित्तीय स्थिति सारांश","Income vs expenses":"आय बनाम खर्च","Last 6 months":"पिछले 6 महीने","Latest activity":"हाल की गतिविधि","MONEY FLOW":"पैसे का प्रवाह","SPENDING":"खर्च","Biggest expense category":"सबसे बड़ी खर्च श्रेणी","No expense categories yet.":"अभी कोई खर्च श्रेणी नहीं है।","Start tracking your money":"अपने पैसे को ट्रैक करना शुरू करें","Your financial picture starts here.":"आपकी वित्तीय तस्वीर यहां से शुरू होती है।","Your financial activity will appear here once you start recording transactions.":"लेन-देन दर्ज करना शुरू करने पर आपकी वित्तीय गतिविधि यहां दिखाई देगी।","Start tracking your transactions":"अपने लेन-देन ट्रैक करना शुरू करें","No major financial alerts based on your current recorded activity.":"मौजूदा दर्ज गतिविधि के आधार पर कोई बड़ा वित्तीय अलर्ट नहीं है।","Spending is getting high":"खर्च बढ़ रहा है","Watch your spending":"अपने खर्च पर ध्यान दें","You're spending more than you earn":"आप आय से अधिक खर्च कर रहे हैं","Your current spending is ahead of your income.":"मौजूदा खर्च आपकी आय से अधिक है।","Your finances are currently in a healthy position.":"आपकी वित्तीय स्थिति अभी स्वस्थ है।","Recommended next step":"अगला सुझाया कदम","Focus area":"ध्यान देने का क्षेत्र","Reduce spending":"खर्च कम करें","View all →":"सभी देखें →","Open →":"खोलें →","QUICK VIEW":"क्विक व्यू","INSIGHT":"इनसाइट","ACTIVITY":"गतिविधि",
"DANGER ZONE":"खतरे का क्षेत्र","Name":"नाम","Country":"देश","Currency":"मुद्रा","Current password":"मौजूदा पासवर्ड","New password":"नया पासवर्ड","Confirm new password":"नए पासवर्ड की पुष्टि करें","Update password":"पासवर्ड अपडेट करें","Delete my account":"मेरा खाता हटाएं","This permanently removes your account and all associated financial data.":"यह आपके खाते और उससे जुड़े सभी वित्तीय डेटा को स्थायी रूप से हटा देगा।","Import / Export":"इम्पोर्ट / एक्सपोर्ट","Download filtered data as CSV or Excel":"फ़िल्टर किया डेटा CSV या Excel में डाउनलोड करें","Issue type":"समस्या का प्रकार","General question":"सामान्य प्रश्न","Bug report":"बग रिपोर्ट","Payments":"भुगतान","Message":"संदेश","Send to Sigora":"SIGORA को भेजें","Support request received. We'll follow up using the email you provided.":"सहायता अनुरोध मिल गया। दिए गए ईमेल पर हम आपसे संपर्क करेंगे।","SMS":"SMS","AI / Insights":"AI / इनसाइट्स",
"Turn your transaction history into clear, practical financial signals.":"अपने लेन-देन इतिहास को स्पष्ट और उपयोगी वित्तीय संकेतों में बदलें।","AVAILABLE IN PREMIUM":"PREMIUM में उपलब्ध","Unlock with Premium →":"Premium से अनलॉक करें →",
"Give yourself something concrete to work toward.":"अपने लिए एक स्पष्ट लक्ष्य तय करें।","No goals yet.":"अभी कोई लक्ष्य नहीं है।","Edit":"संपादित करें","Open insight":"इनसाइट खोलें","✓ Goal completed — you did it.":"✓ लक्ष्य पूरा हुआ — आपने कर दिखाया।","✦ Generate goal insight":"✦ लक्ष्य इनसाइट बनाएं","✦ Goal intelligence":"✦ लक्ष्य इंटेलिजेंस",
"BUDGETS":"बजट","SPENDING CONTROL":"खर्च नियंत्रण","Give every category a limit, then let Sigora help you stay inside it.":"हर श्रेणी की सीमा तय करें और SIGORA को उसके भीतर रहने में मदद करने दें।","+ Add budget":"+ बजट जोड़ें","No budgets yet.":"अभी कोई बजट नहीं है।","Create your first spending limit and start getting better signals from Sigora.":"पहली खर्च सीमा बनाएं और SIGORA से बेहतर संकेत पाना शुरू करें।","Limit":"सीमा","Spent":"खर्च हुआ","ON TRACK":"सही दिशा में","WATCH":"ध्यान दें","View insight":"इनसाइट देखें","✦ Generate AI insight":"✦ AI इनसाइट बनाएं","✦ Sigora AI":"✦ SIGORA AI","MONTH":"महीना",
"MONEY CONTROL":"पैसा नियंत्रण","Every rupee in one place. Search, filter, edit and take your data with you.":"हर रुपया एक जगह। खोजें, फ़िल्टर करें, संपादित करें और अपना डेटा साथ लें।","+ Add transaction":"+ लेन-देन जोड़ें","INCOME":"आय","EXPENSES":"खर्च","BALANCE":"बैलेंस","Filtered total":"फ़िल्टर किया कुल","Income minus expenses":"आय में से खर्च घटाकर","No matching transactions.":"कोई मेल खाता लेन-देन नहीं मिला।","Add a transaction or clear your filters to see your money activity.":"लेन-देन जोड़ें या पैसे की गतिविधि देखने के लिए फ़िल्टर साफ करें।","DATE":"तारीख","DETAILS":"विवरण","TYPE":"प्रकार","AMOUNT":"राशि","ACTION":"कार्रवाई","VISIBLE":"दिखाई दे रहा","↥ Export":"↥ एक्सपोर्ट","MONEY MOVEMENT":"पैसे की आवाजाही","Record it once. Sigora handles the rest.":"एक बार दर्ज करें। बाकी SIGORA संभालता है।","Transaction type":"लेन-देन प्रकार","Leave as Auto to let Sigora decide":"SIGORA को तय करने देने के लिए Auto रखें","Edit Transaction":"लेन-देन संपादित करें","Transaction Type":"लेन-देन प्रकार",
"Understand where your money is going.":"समझें आपका पैसा कहां जा रहा है।","Where Your Money Goes":"आपका पैसा कहां जाता है","Your overall financial picture.":"आपकी पूरी वित्तीय तस्वीर।","Your spending by category.":"श्रेणी के अनुसार आपका खर्च।","Monthly Analysis":"मासिक विश्लेषण","Month Focus":"महीने पर फोकस","This Month":"इस महीने","Last Month":"पिछले महीने","This Year":"इस वर्ष","Continue to Monthly Analysis":"मासिक विश्लेषण जारी रखें","Click a month to explore it.":"देखने के लिए कोई महीना चुनें।","Loading your spending analysis...":"आपका खर्च विश्लेषण लोड हो रहा है...","Analyzing your spending...":"आपके खर्च का विश्लेषण हो रहा है...","💡 Spending Breakdown":"💡 खर्च विवरण","💡 Sigora":"💡 SIGORA","Month":"महीना",
"Know what happens next.":"जानिए आगे क्या होगा।","EXPLAINABLE SCORE":"समझने योग्य स्कोर","Your score begins with real data.":"आपका स्कोर वास्तविक डेटा से शुरू होता है।","What drives your score.":"आपके स्कोर को क्या प्रभावित करता है।","Score":"स्कोर","Signal":"संकेत","Status":"स्थिति","Projected":"अनुमानित","EARLY WARNING ENGINE":"पूर्व चेतावनी इंजन","Intervene before the breach.":"सीमा पार होने से पहले कार्रवाई करें।","WHAT-IF SIMULATOR · PREMIUM":"व्हाट-इफ सिम्युलेटर · PREMIUM","Can I afford this decision?":"क्या मैं यह निर्णय वहन कर सकता हूं?","Model a planned purchase against your recorded savings and goals.":"योजनाबद्ध खरीद को दर्ज बचत और लक्ष्यों के मुकाबले देखें।","Simulate →":"सिम्युलेट करें →","Unlock simulator":"सिम्युलेटर अनलॉक करें","HOW TO UNLOCK":"कैसे अनलॉक करें","Add financial data first":"पहले वित्तीय डेटा जोड़ें","Add income and expense transactions.":"आय और खर्च के लेन-देन जोड़ें।","Build history":"इतिहास बनाएं","More months unlock stronger stability signals.":"अधिक महीनों का डेटा मजबूत स्थिरता संकेत देता है।","Add context":"संदर्भ जोड़ें","Create budgets and track goal progress.":"बजट बनाएं और लक्ष्य प्रगति ट्रैक करें।","Forecasts are estimates from recorded data, not guarantees or regulated financial advice.":"पूर्वानुमान दर्ज डेटा से अनुमान हैं; गारंटी या विनियमित वित्तीय सलाह नहीं।","Only signals backed by your recorded data are included. Missing budgets, goals or history are not assigned artificial neutral scores.":"केवल आपके दर्ज डेटा से समर्थित संकेत शामिल होते हैं। गायब बजट, लक्ष्य या इतिहास को कृत्रिम स्कोर नहीं दिया जाता।","Explainable signals calculated from your recorded finances — before AI turns them into advice.":"AI के समझाने से पहले आपके दर्ज वित्त से गणना किए गए स्पष्ट संकेत।",
"Your money, beyond spending.":"खर्च से आगे आपका पैसा।","Track investments, understand risk and connect your portfolio to your complete financial picture.":"निवेश ट्रैक करें, जोखिम समझें और पोर्टफोलियो को पूरी वित्तीय तस्वीर से जोड़ें।","Tell Sigora what kind of investor you are.":"SIGORA को बताएं आप किस तरह के निवेशक हैं।","Create investor profile →":"निवेशक प्रोफ़ाइल बनाएं →","Current tracked value":"मौजूदा ट्रैक मूल्य","Invested cost":"निवेशित लागत","Gain / loss":"लाभ / हानि","Holding":"होल्डिंग","Value":"मूल्य","No holdings yet. Add your first investment above.":"अभी कोई होल्डिंग नहीं है। ऊपर अपना पहला निवेश जोड़ें।","Find & add":"खोजें और जोड़ें","Your watchlist is empty.":"आपकी वॉचलिस्ट खाली है।","View chart →":"चार्ट देखें →","Monthly contribution":"मासिक योगदान","Assumed annual return %":"मान्य वार्षिक रिटर्न %","Years":"वर्ष","Illustrative ending value":"उदाहरण अंतिम मूल्य","Enter assumptions and calculate a scenario.":"मान्यताएं दर्ज करें और परिदृश्य की गणना करें।","Calculate scenario":"परिदृश्य गणना करें","Change the assumptions yourself. Projections are mathematical illustrations, not forecasts or promised returns.":"मान्यताएं स्वयं बदलें। प्रोजेक्शन गणितीय उदाहरण हैं, पूर्वानुमान या वादा किया रिटर्न नहीं।","These are asset-class examples, not personalized picks.":"ये एसेट-क्लास उदाहरण हैं, व्यक्तिगत चयन नहीं।","This is a generic illustration for learning — not a recommendation for your money.":"यह सीखने के लिए सामान्य उदाहरण है, आपके पैसे के लिए सिफारिश नहीं।","Sigora provides educational analytics, portfolio tracking and risk information. It does not provide personalized buy/sell recommendations, target returns or guarantees.":"SIGORA शैक्षिक एनालिटिक्स, पोर्टफोलियो ट्रैकिंग और जोखिम जानकारी देता है। व्यक्तिगत खरीद/बिक्री सलाह, लक्ष्य रिटर्न या गारंटी नहीं देता।","✦ AI portfolio insight":"✦ AI पोर्टफोलियो इनसाइट","Portfolio insight":"पोर्टफोलियो इनसाइट","AI analysis across your tracked investments and financial readiness.":"आपके ट्रैक किए निवेश और वित्तीय तैयारी पर AI विश्लेषण।","No security recommendations.":"किसी विशिष्ट सिक्योरिटी की सिफारिश नहीं।","Sigora analyses diversification, risk and financial context without telling you what named investment to buy or sell.":"किसी नामित निवेश को खरीदने या बेचने को कहे बिना SIGORA विविधीकरण, जोखिम और वित्तीय संदर्भ का विश्लेषण करता है।","MARKET RESEARCH":"मार्केट रिसर्च","Latest market price":"नवीनतम मार्केट कीमत","Day range":"दिन की रेंज","52-week range":"52-सप्ताह रेंज","Historical chart temporarily unavailable":"ऐतिहासिक चार्ट अस्थायी रूप से उपलब्ध नहीं","What does this mean?":"इसका क्या मतलब है?","Remember:":"याद रखें:","This explains market data; it is not a recommendation to buy, sell or hold this security. Prices can be delayed or temporarily unavailable.":"यह मार्केट डेटा समझाता है; इस सिक्योरिटी को खरीदने, बेचने या रखने की सलाह नहीं है। कीमतें देरी से या अस्थायी रूप से अनुपलब्ध हो सकती हैं।","Sigora will not draw a trend from incomplete market history. Try another period or check again later.":"अधूरे मार्केट इतिहास से SIGORA ट्रेंड नहीं बनाएगा। दूसरी अवधि चुनें या बाद में देखें।","INVESTOR PROFILE":"निवेशक प्रोफ़ाइल","How do you want your money to behave?":"आप अपने पैसे से क्या चाहते हैं?","Educational profiling only.":"केवल शैक्षिक प्रोफ़ाइल।","Investment horizon":"निवेश अवधि","Primary objective":"मुख्य उद्देश्य","Comfort with volatility":"उतार-चढ़ाव सहने की क्षमता","Emergency fund coverage (months)":"आपातकालीन फंड कवरेज (महीने)","Planned monthly investment":"योजनाबद्ध मासिक निवेश","If markets fell sharply":"यदि बाजार तेज़ी से गिरें","Long-term growth":"लंबी अवधि की वृद्धि","Income + stability":"आय + स्थिरता","Preserve capital / lower volatility":"पूंजी सुरक्षित रखना / कम उतार-चढ़ाव","Low — stability matters most":"कम — स्थिरता सबसे महत्वपूर्ण","Moderate — some fluctuations are okay":"मध्यम — कुछ उतार-चढ़ाव ठीक हैं","High — I accept large fluctuations":"उच्च — मैं बड़े उतार-चढ़ाव स्वीकार करता हूं","I would likely reduce exposure":"मैं निवेश जोखिम कम करूंगा","I would usually wait and review":"मैं आमतौर पर इंतजार करके समीक्षा करूंगा","I could tolerate adding more":"मैं और जोड़ने पर विचार कर सकता हूं","Build my profile →":"मेरी प्रोफ़ाइल बनाएं →","This does not recommend specific securities or guarantee returns.":"यह किसी विशिष्ट सिक्योरिटी की सिफारिश या रिटर्न की गारंटी नहीं देता।",
"Welcome back.":"वापसी पर स्वागत है।","Your money, your picture, your next move.":"आपका पैसा, आपकी तस्वीर, आपका अगला कदम।","Log In":"लॉग इन","Forgot password?":"पासवर्ड भूल गए?","Don't have an account?":"खाता नहीं है?","Create one":"खाता बनाएं","Create your Sigora.":"अपना SIGORA खाता बनाएं।","Build a clearer picture of where your money goes.":"समझें आपका पैसा कहां जा रहा है।","Create Account":"खाता बनाएं","Already have an account?":"पहले से खाता है?","START FRESH":"नई शुरुआत","ACCOUNT RECOVERY":"खाता रिकवरी","Reset your password.":"अपना पासवर्ड रीसेट करें।","Enter the email linked to your Sigora account. We'll send a secure, single-use reset link that expires in 30 minutes.":"अपने SIGORA खाते से जुड़ा ईमेल दर्ज करें। हम 30 मिनट में समाप्त होने वाला सुरक्षित एक-बार उपयोग लिंक भेजेंगे।","Send reset link":"रीसेट लिंक भेजें","← Back to login":"← लॉगिन पर वापस","Choose a new password.":"नया पासवर्ड चुनें।","Request a new link":"नया लिंक मांगें","This reset link is invalid, expired, or has already been used.":"यह रीसेट लिंक अमान्य, समाप्त या पहले उपयोग हो चुका है।","Use at least 8 characters. Once saved, this reset link cannot be used again.":"कम से कम 8 अक्षर इस्तेमाल करें। सेव होने के बाद यह लिंक फिर उपयोग नहीं हो सकता।","We're here to help.":"हम मदद के लिए यहां हैं।","If something looks wrong, you find a bug, or you have a question about Sigora, contact us.":"कुछ गलत लगे, बग मिले या SIGORA के बारे में सवाल हो तो हमसे संपर्क करें।","Account and data requests":"खाता और डेटा अनुरोध","For account-specific help, email us from the address associated with your Sigora account when possible. Never send passwords, OTPs, card PINs, API keys, or full banking credentials.":"खाता सहायता के लिए संभव हो तो SIGORA खाते से जुड़े ईमेल से लिखें। पासवर्ड, OTP, कार्ड PIN, API key या पूरी बैंक लॉगिन जानकारी कभी न भेजें।","You can manage many settings directly inside Sigora. Account deletion is available in Settings. If you cannot access your account or need help with a data request, email support.":"कई सेटिंग्स SIGORA में सीधे संभाली जा सकती हैं। खाता हटाने का विकल्प सेटिंग्स में है। खाते तक पहुंच न हो या डेटा अनुरोध में सहायता चाहिए तो सपोर्ट को ईमेल करें।"
}}
for _lang, _items in _ULTIMATE_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_TRANSLATIONS[_lang].update(_items)
    SIGORA_PHRASE_TRANSLATIONS[_lang].update(_items)


_FINAL_VISIBLE_I18N={
"ta":{
"Another step toward the money you want.":"நீங்கள் விரும்பும் நிதிநிலைக்கான இன்னொரு படி.","Budget managed! 💚":"பட்ஜெட் கட்டுப்பாட்டில்! 💚","Explain your money":"உங்கள் பணத்தைப் புரிந்துகொள்ளுங்கள்","GOAL MOMENTUM":"இலக்கு முன்னேற்றம்","GOOD HABIT":"நல்ல பழக்கம்","Goal completed! 🎉":"இலக்கு நிறைவேறியது! 🎉","Goal saved! 🎯":"இலக்கு சேமிக்கப்பட்டது! 🎯","Keep going":"தொடர்ந்து செல்லுங்கள்","Know what happens next":"அடுத்து என்ன நடக்கும் என்பதை அறியுங்கள்","MILESTONE UNLOCKED":"மைல்கல் திறக்கப்பட்டது","Nice move! ✦":"அருமையான முன்னேற்றம்! ✦","You just turned a financial target into a finished goal.":"ஒரு நிதி இலக்கை நீங்கள் வெற்றிகரமாக நிறைவேற்றிவிட்டீர்கள்.","You're giving every rupee a job.":"ஒவ்வொரு ரூபாய்க்கும் நீங்கள் ஒரு நோக்கம் கொடுக்கிறீர்கள்.","Your financial activity just earned progress.":"உங்கள் நிதிச் செயல்பாடு புதிய முன்னேற்றத்தை உருவாக்கியது.","© 2026 SIGORA · Public Beta":"© 2026 SIGORA · பொது பீட்டா","10× Consistent":"10× தொடர்ச்சி","Add a few transactions and Sigora will start turning your financial activity into useful patterns, spending signals and insights.":"சில பரிவர்த்தனைகளைச் சேருங்கள்; உங்கள் நிதிச் செயல்பாட்டை பயனுள்ள போக்குகள், செலவு சிக்னல்கள் மற்றும் நுண்ணறிவுகளாக SIGORA மாற்றத் தொடங்கும்.","Add transactions from the Transactions page to start building your spending picture.":"உங்கள் செலவுப் படத்தை உருவாக்க பரிவர்த்தனைகள் பக்கத்தில் பரிவர்த்தனைகளைச் சேர்க்கவும்.","Add your first transaction from the Transactions page to unlock useful financial insights.":"பயனுள்ள நிதி நுண்ணறிவுகளைத் திறக்க பரிவர்த்தனைகள் பக்கத்தில் முதல் பரிவர்த்தனையைச் சேர்க்கவும்.","More than 80% of your recorded income has gone toward expenses.":"நீங்கள் பதிவு செய்த வருமானத்தின் 80%-க்கும் அதிகம் செலவுகளுக்குச் சென்றுள்ளது.","You're doing okay, but your spending deserves attention.":"நிலை சரியாக உள்ளது, ஆனால் உங்கள் செலவில் கவனம் தேவை.","Your recorded expenses are currently higher than your recorded income.":"பதிவு செய்த செலவுகள் தற்போது பதிவு செய்த வருமானத்தை விட அதிகம்.","◎ Goal setter":"◎ இலக்கு அமைப்பவர்","◫ Budget builder":"◫ பட்ஜெட் உருவாக்குபவர்","✦ First move":"✦ முதல் முன்னேற்றம்","🏆 Goal achiever":"🏆 இலக்கு சாதனையாளர்","🔥 7-day streak":"🔥 7 நாள் தொடர்ச்சி","Budget":"பட்ஜெட்","Correction":"திருத்த நடவடிக்கை","EARLY SIGNAL · Add more history to improve confidence":"ஆரம்ப சிக்னல் · நம்பகத்தன்மையை உயர்த்த மேலும் வரலாறு சேர்க்கவும்","ESTABLISHED SIGNAL":"நிலையான சிக்னல்","GROWING CONFIDENCE":"வளரும் நம்பகத்தன்மை","Record activity":"செயல்பாட்டைப் பதிவு செய்","SIMULATION RESULT":"சிமுலேஷன் முடிவு","Answer a short risk-and-horizon questionnaire to unlock model allocation education and better portfolio warnings.":"மாதிரி சொத்து ஒதுக்கீட்டு கல்வி மற்றும் சிறந்த போர்ட்ஃபோலியோ எச்சரிக்கைகளைப் பெற குறுகிய அபாய மற்றும் காலவரம்பு கேள்வித்தாளை நிரப்புங்கள்.","Cash / liquid":"பணம் / திரவ சொத்து","Enter what you own and update current prices whenever you want. Live brokerage syncing can be added later through a supported provider.":"உங்களிடம் உள்ள முதலீடுகளை பதிவு செய்து, விரும்பும் போது தற்போதைய விலைகளைப் புதுப்பிக்கவும். ஆதரிக்கப்படும் சேவை மூலம் நேரடி ப்ரோக்கரேஜ் ஒத்திசைவை பின்னர் சேர்க்கலாம்.","Fixed income":"நிலையான வருமானம்","Gold":"தங்கம்","Index fund / ETF":"இண்டெக்ஸ் ஃபண்ட் / ETF","Mutual fund":"மியூச்சுவல் ஃபண்ட்","Starting amount":"தொடக்க தொகை","Stock":"பங்கு","Type a company, ETF, fund or index name. Sigora will resolve its market ticker automatically when market data is available.":"நிறுவனம், ETF, ஃபண்ட் அல்லது குறியீட்டு பெயரை உள்ளிடுங்கள். சந்தைத் தரவு கிடைக்கும் போது SIGORA அதன் டிக்கரை தானாக கண்டறியும்.","Build an educational risk profile so Sigora can explain your portfolio in the right context.":"உங்கள் போர்ட்ஃபோலியோவை சரியான சூழலில் விளக்க SIGORA-க்கு உதவும் கல்வி சார்ந்த அபாய சுயவிவரத்தை உருவாக்குங்கள்.","← Portfolio":"← போர்ட்ஃபோலியோ","← Back to Invest":"← முதலீட்டுக்கு திரும்பு","← Invest":"← முதலீடு","Everything at a glance.":"எல்லாவற்றையும் ஒரே பார்வையில்.","Live checkout is not configured yet. Add your Razorpay credentials after your merchant account is ready.":"நேரடி கட்டண வசதி இன்னும் அமைக்கப்படவில்லை. உங்கள் merchant கணக்கு தயாரானதும் Razorpay விவரங்களைச் சேர்க்கவும்.","✦ ACTIVE":"✦ செயல்பாட்டில்","Income vs Expenses":"வருமானம் vs செலவுகள்","Password updated. You can log in with your new password.":"கடவுச்சொல் புதுப்பிக்கப்பட்டது. புதிய கடவுச்சொல்லுடன் உள்நுழையலாம்.","Sigora Premium":"SIGORA Premium","Removing the account keeps its existing transactions, but marks them as unassigned.":"கணக்கை நீக்கினாலும் ஏற்கனவே உள்ள பரிவர்த்தனைகள் பாதுகாக்கப்படும்; அவை ஒதுக்கப்படாததாக குறிக்கப்படும்.","Sigora Premium uses Razorpay for recurring subscription payments. You are charged only after you deliberately complete Razorpay checkout. You can request cancellation from the Premium page; cancellation is scheduled for the end of the current billing cycle. For billing problems, contact support from the email linked to your Sigora account.":"SIGORA Premium தொடர்ச்சியான சந்தா கட்டணங்களுக்கு Razorpay-ஐ பயன்படுத்துகிறது. Razorpay கட்டணத்தை நீங்கள் திட்டமிட்டு நிறைவு செய்த பிறகே கட்டணம் வசூலிக்கப்படும். Premium பக்கத்தில் ரத்துசெய்ய கோரலாம்; தற்போதைய பில்லிங் சுழற்சி முடிவில் ரத்து அமலாகும். கட்டண சிக்கல்களுக்கு SIGORA கணக்குடன் இணைந்த மின்னஞ்சலிலிருந்து உதவியைத் தொடர்புகொள்ளவும்.","Predictive Risk Engine":"முன்கணிப்பு அபாய இயந்திரம்","Detect likely budget breaches before month-end and calculate a practical daily correction.":"மாத இறுதிக்கு முன் ஏற்படக்கூடிய பட்ஜெட் மீறல்களை கண்டறிந்து நடைமுறை தினசரி திருத்தத்தை கணக்கிடுகிறது.","An explainable 0–100 score across savings, budgets, goals and cash-flow stability.":"சேமிப்பு, பட்ஜெட், இலக்குகள் மற்றும் பண ஓட்ட நிலைத்தன்மையை அடிப்படையாகக் கொண்ட விளக்கக்கூடிய 0–100 மதிப்பெண்.","What-if Simulator":"என்ன-ஆகும் சிமுலேட்டர்","Model a planned purchase against your recorded savings and goals before you spend.":"செலவிடுவதற்கு முன் திட்டமிட்ட வாங்குதலை உங்கள் சேமிப்புகள் மற்றும் இலக்குகளுடன் ஒப்பிட்டு பாருங்கள்.","AI explanations grounded in Sigora's deterministic financial signals.":"SIGORA-வின் கணக்கிடப்பட்ட நிதிச் சிக்னல்களை அடிப்படையாகக் கொண்ட AI விளக்கங்கள்.","Advanced Reports":"மேம்பட்ட அறிக்கைகள்","Deeper spending, trend and cash-flow analysis.":"ஆழமான செலவு, போக்கு மற்றும் பண ஓட்ட பகுப்பாய்வு.","Advanced Goal Intelligence":"மேம்பட்ட இலக்கு நுண்ணறிவு","Connect spending decisions with the goals they can accelerate or delay.":"செலவு முடிவுகள் உங்கள் இலக்குகளை எவ்வாறு விரைவுபடுத்தலாம் அல்லது தாமதப்படுத்தலாம் என்பதை இணைத்து காட்டுகிறது.","30 AI analyses / month":"மாதத்திற்கு 30 AI பகுப்பாய்வுகள்","A larger AI allowance with built-in platform safety limits.":"உள்ளமைக்கப்பட்ட பாதுகாப்பு வரம்புகளுடன் அதிக AI பயன்பாட்டு அளவு."
},
"hi":{
"Another step toward the money you want.":"आपके मनचाहे वित्तीय भविष्य की ओर एक और कदम।","Budget managed! 💚":"बजट संभल गया! 💚","Explain your money":"अपने पैसे को समझें","GOAL MOMENTUM":"लक्ष्य प्रगति","GOOD HABIT":"अच्छी आदत","Goal completed! 🎉":"लक्ष्य पूरा हुआ! 🎉","Goal saved! 🎯":"लक्ष्य सेव हुआ! 🎯","Keep going":"जारी रखें","Know what happens next":"जानिए आगे क्या होगा","MILESTONE UNLOCKED":"माइलस्टोन अनलॉक","Nice move! ✦":"अच्छी प्रगति! ✦","You just turned a financial target into a finished goal.":"आपने एक वित्तीय लक्ष्य सफलतापूर्वक पूरा कर लिया।","You're giving every rupee a job.":"आप हर रुपये को एक उद्देश्य दे रहे हैं।","Your financial activity just earned progress.":"आपकी वित्तीय गतिविधि ने नई प्रगति बनाई।","© 2026 SIGORA · Public Beta":"© 2026 SIGORA · पब्लिक बीटा","10× Consistent":"10× निरंतर","Add a few transactions and Sigora will start turning your financial activity into useful patterns, spending signals and insights.":"कुछ लेन-देन जोड़ें और SIGORA आपकी वित्तीय गतिविधि को उपयोगी पैटर्न, खर्च संकेत और इनसाइट्स में बदलना शुरू करेगा।","Add transactions from the Transactions page to start building your spending picture.":"अपने खर्च की तस्वीर बनाने के लिए लेन-देन पेज से लेन-देन जोड़ें।","Add your first transaction from the Transactions page to unlock useful financial insights.":"उपयोगी वित्तीय इनसाइट्स अनलॉक करने के लिए लेन-देन पेज से पहला लेन-देन जोड़ें।","More than 80% of your recorded income has gone toward expenses.":"आपकी दर्ज आय का 80% से अधिक खर्च में चला गया है।","You're doing okay, but your spending deserves attention.":"स्थिति ठीक है, लेकिन खर्च पर ध्यान देने की जरूरत है।","Your recorded expenses are currently higher than your recorded income.":"दर्ज खर्च अभी दर्ज आय से अधिक है।","◎ Goal setter":"◎ लक्ष्य निर्माता","◫ Budget builder":"◫ बजट निर्माता","✦ First move":"✦ पहला कदम","🏆 Goal achiever":"🏆 लक्ष्य विजेता","🔥 7-day streak":"🔥 7-दिन स्ट्रीक","Budget":"बजट","Correction":"सुधार","EARLY SIGNAL · Add more history to improve confidence":"प्रारंभिक संकेत · भरोसा बढ़ाने के लिए और इतिहास जोड़ें","ESTABLISHED SIGNAL":"स्थापित संकेत","GROWING CONFIDENCE":"बढ़ता भरोसा","Record activity":"गतिविधि दर्ज करें","SIMULATION RESULT":"सिम्युलेशन परिणाम","Answer a short risk-and-horizon questionnaire to unlock model allocation education and better portfolio warnings.":"मॉडल एसेट आवंटन शिक्षा और बेहतर पोर्टफोलियो चेतावनी के लिए छोटा जोखिम व अवधि प्रश्नपत्र पूरा करें।","Cash / liquid":"नकद / लिक्विड","Enter what you own and update current prices whenever you want. Live brokerage syncing can be added later through a supported provider.":"अपनी होल्डिंग दर्ज करें और जब चाहें मौजूदा कीमतें अपडेट करें। समर्थित प्रदाता के जरिए लाइव ब्रोकरेज सिंक बाद में जोड़ा जा सकता है।","Fixed income":"फिक्स्ड इनकम","Gold":"सोना","Index fund / ETF":"इंडेक्स फंड / ETF","Mutual fund":"म्यूचुअल फंड","Starting amount":"शुरुआती राशि","Stock":"स्टॉक","Type a company, ETF, fund or index name. Sigora will resolve its market ticker automatically when market data is available.":"कंपनी, ETF, फंड या इंडेक्स का नाम लिखें। मार्केट डेटा उपलब्ध होने पर SIGORA उसका टिकर अपने आप खोजेगा।","Build an educational risk profile so Sigora can explain your portfolio in the right context.":"एक शैक्षिक जोखिम प्रोफ़ाइल बनाएं ताकि SIGORA आपके पोर्टफोलियो को सही संदर्भ में समझा सके।","← Portfolio":"← पोर्टफोलियो","← Back to Invest":"← निवेश पर वापस","← Invest":"← निवेश","Everything at a glance.":"सब कुछ एक नज़र में।","Live checkout is not configured yet. Add your Razorpay credentials after your merchant account is ready.":"लाइव चेकआउट अभी कॉन्फ़िगर नहीं है। merchant खाता तैयार होने के बाद Razorpay विवरण जोड़ें।","✦ ACTIVE":"✦ सक्रिय","Income vs Expenses":"आय बनाम खर्च","Password updated. You can log in with your new password.":"पासवर्ड अपडेट हो गया। अब नए पासवर्ड से लॉग इन कर सकते हैं।","Sigora Premium":"SIGORA Premium","Removing the account keeps its existing transactions, but marks them as unassigned.":"खाता हटाने पर मौजूदा लेन-देन सुरक्षित रहते हैं, लेकिन बिना खाते के चिह्नित हो जाते हैं।","Sigora Premium uses Razorpay for recurring subscription payments. You are charged only after you deliberately complete Razorpay checkout. You can request cancellation from the Premium page; cancellation is scheduled for the end of the current billing cycle. For billing problems, contact support from the email linked to your Sigora account.":"SIGORA Premium आवर्ती सदस्यता भुगतान के लिए Razorpay का उपयोग करता है। शुल्क तभी लगता है जब आप जानबूझकर Razorpay चेकआउट पूरा करते हैं। Premium पेज से रद्द करने का अनुरोध किया जा सकता है; रद्द करना मौजूदा बिलिंग चक्र के अंत में लागू होगा। बिलिंग समस्या के लिए SIGORA खाते से जुड़े ईमेल से सहायता से संपर्क करें।","Predictive Risk Engine":"पूर्वानुमानित जोखिम इंजन","Detect likely budget breaches before month-end and calculate a practical daily correction.":"महीने के अंत से पहले संभावित बजट सीमा उल्लंघन पहचानकर व्यावहारिक दैनिक सुधार की गणना करता है।","An explainable 0–100 score across savings, budgets, goals and cash-flow stability.":"बचत, बजट, लक्ष्य और कैश-फ्लो स्थिरता पर आधारित समझने योग्य 0–100 स्कोर।","What-if Simulator":"व्हाट-इफ सिम्युलेटर","Model a planned purchase against your recorded savings and goals before you spend.":"खर्च करने से पहले योजनाबद्ध खरीद को दर्ज बचत और लक्ष्यों के मुकाबले देखें।","AI explanations grounded in Sigora's deterministic financial signals.":"SIGORA के गणना किए वित्तीय संकेतों पर आधारित AI व्याख्याएं।","Advanced Reports":"उन्नत रिपोर्ट","Deeper spending, trend and cash-flow analysis.":"गहरा खर्च, ट्रेंड और कैश-फ्लो विश्लेषण।","Advanced Goal Intelligence":"उन्नत लक्ष्य इंटेलिजेंस","Connect spending decisions with the goals they can accelerate or delay.":"दिखाता है कि खर्च के निर्णय लक्ष्यों को तेज़ या धीमा कैसे कर सकते हैं।","30 AI analyses / month":"महीने में 30 AI विश्लेषण","A larger AI allowance with built-in platform safety limits.":"प्लेटफ़ॉर्म सुरक्षा सीमाओं के साथ अधिक AI उपयोग।"
}}
for _lang,_items in _FINAL_VISIBLE_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_TRANSLATIONS[_lang].update(_items)
    SIGORA_PHRASE_TRANSLATIONS[_lang].update(_items)


_BALANCE_SHEET_I18N = {
"en": {
"total_cash":"Total cash","tracked_cash":"Tracked bank, wallet and cash balances","investments_value":"Investments","tracked_investments":"Current value of tracked investments","liabilities":"Liabilities","tracked_liabilities":"Credit cards, loans and other tracked debt","net_worth":"Net worth","assets_minus_liabilities":"Cash + investments − liabilities","this_month_income":"This month income","this_month_expenses":"This month expenses","monthly_cashflow":"Recorded this month","loan":"Loan","liability":"Other liability","outstanding_balance_optional":"Outstanding balance (optional)","balance_or_outstanding_optional":"Current / outstanding balance (optional)","balance_checkpoint_help":"For bank/cash accounts, enter the balance you have now. Future manual transactions update the displayed balance. For credit cards and loans, enter the amount currently owed.",
"ai_daily_limit_reached":"AI daily limit reached ({limit}/day). Please try again tomorrow.","ai_monthly_budget_reached":"SIGORA AI monthly safety budget has been reached. AI is paused until the next billing month.","ai_platform_limit_reached":"SIGORA AI has reached its platform safety limit for this month. Please try again later.","ai_monthly_limit_reached":"AI monthly limit reached ({limit}/month). Upgrade to Premium for a larger monthly allowance.",
"AI Insights":"AI Insights","Turn your transaction history into clear, practical financial signals.":"Turn your transaction history into clear, practical financial signals.","Premium active":"Premium active","AI usage":"AI usage","analyses this month":"analyses this month","PERSONALIZED":"PERSONALIZED","Your latest analysis":"Your latest analysis","Advanced spending patterns":"Advanced spending patterns","See deeper category and habit patterns across your history.":"See deeper category and habit patterns across your history.","Income & expense forecast":"Income & expense forecast","Get forward-looking estimates based on your recorded history.":"Get forward-looking estimates based on your recorded history.","Personalized recommendations":"Personalized recommendations","Receive practical, data-grounded suggestions tailored to your activity.":"Receive practical, data-grounded suggestions tailored to your activity.","Connect your spending habits to the goals you care about.":"Connect your spending habits to the goals you care about.","AVAILABLE IN PREMIUM":"AVAILABLE IN PREMIUM","Unlock with Premium →":"Unlock with Premium →"},
"ta": {
"total_cash":"மொத்த பண இருப்பு","tracked_cash":"பதிவு செய்யப்பட்ட வங்கி, வாலெட் மற்றும் பண இருப்புகள்","investments_value":"முதலீடுகள்","tracked_investments":"பதிவு செய்யப்பட்ட முதலீடுகளின் தற்போதைய மதிப்பு","liabilities":"கடன்கள்","tracked_liabilities":"கிரெடிட் கார்டு, கடன் மற்றும் பிற பதிவு செய்யப்பட்ட பொறுப்புகள்","net_worth":"நிகர சொத்து மதிப்பு","assets_minus_liabilities":"பணம் + முதலீடுகள் − கடன்கள்","this_month_income":"இந்த மாத வருமானம்","this_month_expenses":"இந்த மாத செலவுகள்","monthly_cashflow":"இந்த மாதம் பதிவு செய்யப்பட்டவை","loan":"கடன்","liability":"பிற கடன் பொறுப்பு","outstanding_balance_optional":"நிலுவைத் தொகை (விருப்பம்)","balance_or_outstanding_optional":"தற்போதைய / நிலுவை இருப்பு (விருப்பம்)","balance_checkpoint_help":"வங்கி/பணக் கணக்குகளுக்கு இப்போது உள்ள இருப்பை பதிவு செய்யுங்கள்; அதன் பிறகு சேர்க்கும் கைமுறை பரிவர்த்தனைகள் காட்டப்படும் இருப்பை புதுப்பிக்கும். கிரெடிட் கார்டு மற்றும் கடன்களுக்கு தற்போது செலுத்த வேண்டிய நிலுவைத் தொகையை பதிவு செய்யுங்கள்.",
"ai_daily_limit_reached":"AI தினசரி வரம்பு ({limit}/நாள்) எட்டப்பட்டது. நாளை மீண்டும் முயற்சிக்கவும்.","ai_monthly_budget_reached":"SIGORA AI மாதாந்திர பாதுகாப்பு செலவு வரம்பு எட்டப்பட்டது. அடுத்த பில்லிங் மாதம் வரை AI நிறுத்தப்பட்டுள்ளது.","ai_platform_limit_reached":"இந்த மாதத்திற்கான SIGORA AI தள பாதுகாப்பு வரம்பு எட்டப்பட்டது. பின்னர் மீண்டும் முயற்சிக்கவும்.","ai_monthly_limit_reached":"AI மாதாந்திர வரம்பு ({limit}/மாதம்) எட்டப்பட்டது. அதிக மாதாந்திர பயன்பாட்டிற்கு Premium-க்கு மேம்படுத்தவும்.",
"AI Insights":"AI நிதி நுண்ணறிவு","Turn your transaction history into clear, practical financial signals.":"உங்கள் பரிவர்த்தனை வரலாற்றை தெளிவான, நடைமுறை நிதிச் சிக்னல்களாக மாற்றுங்கள்.","Premium active":"Premium செயல்பாட்டில்","AI usage":"AI பயன்பாடு","analyses this month":"இந்த மாத பகுப்பாய்வுகள்","PERSONALIZED":"தனிப்பயன்","Your latest analysis":"உங்கள் சமீபத்திய பகுப்பாய்வு","Advanced spending patterns":"மேம்பட்ட செலவு முறைகள்","See deeper category and habit patterns across your history.":"உங்கள் வரலாற்றில் உள்ள செலவு பிரிவுகள் மற்றும் பழக்கங்களை ஆழமாகப் பாருங்கள்.","Income & expense forecast":"வருமானம் மற்றும் செலவு கணிப்பு","Get forward-looking estimates based on your recorded history.":"நீங்கள் பதிவு செய்த வரலாற்றை அடிப்படையாகக் கொண்டு எதிர்கால மதிப்பீடுகளைப் பெறுங்கள்.","Personalized recommendations":"தனிப்பயன் பரிந்துரைகள்","Receive practical, data-grounded suggestions tailored to your activity.":"உங்கள் செயல்பாட்டை அடிப்படையாகக் கொண்ட நடைமுறை பரிந்துரைகளைப் பெறுங்கள்.","Connect your spending habits to the goals you care about.":"உங்கள் செலவு பழக்கங்கள் உங்கள் முக்கிய இலக்குகளுடன் எவ்வாறு தொடர்புடையவை என்பதைப் பாருங்கள்.","AVAILABLE IN PREMIUM":"PREMIUM-ல் கிடைக்கும்","Unlock with Premium →":"Premium மூலம் திறக்கவும் →"},
"hi": {
"total_cash":"कुल नकद","tracked_cash":"दर्ज बैंक, वॉलेट और नकद बैलेंस","investments_value":"निवेश","tracked_investments":"दर्ज निवेशों का मौजूदा मूल्य","liabilities":"देयताएँ","tracked_liabilities":"क्रेडिट कार्ड, लोन और अन्य दर्ज कर्ज","net_worth":"नेट वर्थ","assets_minus_liabilities":"नकद + निवेश − देयताएँ","this_month_income":"इस महीने की आय","this_month_expenses":"इस महीने का खर्च","monthly_cashflow":"इस महीने दर्ज","loan":"लोन","liability":"अन्य देयता","outstanding_balance_optional":"बकाया राशि (वैकल्पिक)","balance_or_outstanding_optional":"मौजूदा / बकाया बैलेंस (वैकल्पिक)","balance_checkpoint_help":"बैंक/नकद खातों के लिए अभी का बैलेंस दर्ज करें; इसके बाद जो मैनुअल लेन-देन जोड़ेंगे वे दिखने वाले बैलेंस को अपडेट करेंगे। क्रेडिट कार्ड और लोन के लिए अभी बकाया राशि दर्ज करें।",
"ai_daily_limit_reached":"AI की दैनिक सीमा ({limit}/दिन) पूरी हो गई है। कृपया कल फिर कोशिश करें।","ai_monthly_budget_reached":"SIGORA AI का मासिक सुरक्षा बजट पूरा हो गया है। अगले बिलिंग महीने तक AI रुका रहेगा।","ai_platform_limit_reached":"इस महीने SIGORA AI की प्लेटफ़ॉर्म सुरक्षा सीमा पूरी हो गई है। कृपया बाद में फिर कोशिश करें।","ai_monthly_limit_reached":"AI की मासिक सीमा ({limit}/माह) पूरी हो गई है। अधिक मासिक उपयोग के लिए Premium लें।",
"AI Insights":"AI इनसाइट्स","Turn your transaction history into clear, practical financial signals.":"अपने लेन-देन इतिहास को साफ और उपयोगी वित्तीय संकेतों में बदलें।","Premium active":"Premium सक्रिय","AI usage":"AI उपयोग","analyses this month":"इस महीने के विश्लेषण","PERSONALIZED":"व्यक्तिगत","Your latest analysis":"आपका नवीनतम विश्लेषण","Advanced spending patterns":"उन्नत खर्च पैटर्न","See deeper category and habit patterns across your history.":"अपने इतिहास में श्रेणी और खर्च की आदतों को गहराई से देखें।","Income & expense forecast":"आय और खर्च का पूर्वानुमान","Get forward-looking estimates based on your recorded history.":"दर्ज इतिहास के आधार पर आगे के अनुमान देखें।","Personalized recommendations":"व्यक्तिगत सुझाव","Receive practical, data-grounded suggestions tailored to your activity.":"आपकी गतिविधि पर आधारित व्यावहारिक सुझाव पाएं।","Connect your spending habits to the goals you care about.":"अपनी खर्च की आदतों को महत्वपूर्ण लक्ष्यों से जोड़कर देखें।","AVAILABLE IN PREMIUM":"PREMIUM में उपलब्ध","Unlock with Premium →":"Premium से अनलॉक करें →"}
}
for _lang, _items in _BALANCE_SHEET_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_TRANSLATIONS[_lang].update(_items)
    SIGORA_PHRASE_TRANSLATIONS[_lang].update(_items)

# Stability/translation repair: landing copy and common runtime labels.
_REPAIR_I18N = {
    "en": {},
    "ta": {
        "PERSONAL FINANCE · REIMAGINED":"தனிநபர் நிதி · புதுமையாக",
        "Know your money.":"உங்கள் பணத்தை அறிந்துகொள்ளுங்கள்.",
        "Own your future.":"உங்கள் எதிர்காலத்தை கட்டுப்படுத்துங்கள்.",
        "A smarter way to track your spending, understand your finances, and build better financial habits.":"உங்கள் செலவுகளை கண்காணித்து, நிதிநிலையை புரிந்துகொண்டு, சிறந்த நிதிப் பழக்கங்களை உருவாக்க ஒரு புத்திசாலியான வழி.",
        "Continue to Sigora":"SIGORA-க்கு தொடரவும்", "Enter Sigora":"SIGORA-க்கு செல்லவும்", "View transactions":"பரிவர்த்தனைகளைப் பார்க்கவும்",
        "Current balance":"தற்போதைய இருப்பு", "Money in":"உள்ளே வந்த பணம்", "Money out":"வெளியே சென்ற பணம்", "Account activity":"கணக்கு செயல்பாடு",
        "Recent transactions":"சமீபத்திய பரிவர்த்தனைகள்", "Top spending categories":"அதிக செலவு பிரிவுகள்"
    },
    "hi": {
        "PERSONAL FINANCE · REIMAGINED":"पर्सनल फाइनेंस · नए अंदाज़ में",
        "Know your money.":"अपने पैसे को जानें।",
        "Own your future.":"अपने भविष्य पर नियंत्रण रखें।",
        "A smarter way to track your spending, understand your finances, and build better financial habits.":"अपने खर्च को ट्रैक करने, वित्त को समझने और बेहतर वित्तीय आदतें बनाने का एक स्मार्ट तरीका।",
        "Continue to Sigora":"SIGORA में आगे बढ़ें", "Enter Sigora":"SIGORA में प्रवेश करें", "View transactions":"लेन-देन देखें",
        "Current balance":"मौजूदा बैलेंस", "Money in":"आने वाला पैसा", "Money out":"जाने वाला पैसा", "Account activity":"खाता गतिविधि",
        "Recent transactions":"हाल के लेन-देन", "Top spending categories":"सबसे अधिक खर्च की श्रेणियां"
    }
}
for _lang, _items in _REPAIR_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {})
    SIGORA_TRANSLATIONS[_lang].update(_items)
    SIGORA_PHRASE_TRANSLATIONS[_lang].update(_items)

_INVEST_V2_I18N = {
"en": {
"portfolio_intelligence":"Portfolio Intelligence","current_value":"Current value","today_change":"Today's change","tracked_return":"Tracked return","portfolio_health":"Portfolio Health","portfolio_health_sub":"Explainable signals from your tracked holdings and financial context.","your_holdings":"Your holdings","top_holdings":"Top holdings","view_all_holdings":"View all holdings","hide_all_holdings":"Show fewer holdings","search_holdings":"Search holdings","sort_by":"Sort by","current_value_sort":"Current value","return_sort":"Return","name_sort":"Name","avg_bought_price":"Avg bought price","latest_price":"Latest price","auto_market_price":"Auto market price","manual_fallback_price":"Current price (only if market data is unavailable)","market_price_help":"SIGORA refreshes supported market prices automatically. Bought price stays as your recorded cost basis.","price_delayed":"Market prices can be delayed or temporarily unavailable.","last_price_sync":"Last market sync","goal_connection":"Goal Connection","goal_connection_sub":"See how your tracked portfolio compares with the goals you are building toward — without treating market value as guaranteed goal funding.","portfolio_equals_goal":"Portfolio equals {pct}% of this goal target","no_goals_connect":"Create a goal to connect your investments to something you are building toward.","portfolio_to_life":"Portfolio → Life","portfolio_to_life_sub":"See what your investments mean for your complete financial position.","of_net_worth_invested":"of your current net worth is represented by tracked investments","largest_holding":"Largest holding","emergency_cover":"Emergency cover","months_short":"months","downside_20":"If the portfolio fell 20%","net_worth_change":"estimated net-worth change","scenario_lab":"Scenario Lab","scenario_lab_sub":"Explore mathematical scenarios — not forecasts or promised returns.","explore_scenarios":"Explore scenarios","portfolio_drop":"Portfolio change %","estimated_portfolio":"Estimated portfolio value","estimated_net_worth":"Estimated net worth","apply_scenario":"Calculate scenario","holdings_count":"holdings","refresh_prices":"Refresh market prices","prices_refreshed":"Market prices refreshed where available.","price_refresh_partial":"Some market prices could not be refreshed right now.","add_holding":"Add holding","investment_name":"Investment name","symbol_optional":"Symbol (optional)","quantity":"Quantity","average_cost":"Average cost / bought price","notes_optional":"Notes (optional)","portfolio_value":"Portfolio value","gain_loss":"Gain / loss","market_unavailable":"Market unavailable","cost_basis":"Cost basis","portfolio_share":"Portfolio share","remove_holding":"Remove this holding?","no_holdings":"No holdings yet. Add your first investment above.","goal_saved_amount":"Goal savings recorded","goal_target":"Target","portfolio_reference":"Portfolio reference","not_guaranteed":"Not guaranteed funding","portfolio_health_not_advice":"This score is educational and based only on recorded data; it is not investment advice.","price_source":"Price source","market_data_may_be_delayed":"market data may be delayed"
},
"ta": {
"portfolio_intelligence":"போர்ட்ஃபோலியோ நுண்ணறிவு","current_value":"தற்போதைய மதிப்பு","today_change":"இன்றைய மாற்றம்","tracked_return":"பதிவான வருமான விகிதம்","portfolio_health":"போர்ட்ஃபோலியோ ஆரோக்கியம்","portfolio_health_sub":"உங்கள் பதிவு செய்யப்பட்ட முதலீடுகள் மற்றும் நிதிச் சூழலை அடிப்படையாகக் கொண்ட விளக்கமான சிக்னல்கள்.","your_holdings":"உங்கள் முதலீடுகள்","top_holdings":"முக்கிய முதலீடுகள்","view_all_holdings":"அனைத்து முதலீடுகளையும் பார்","hide_all_holdings":"குறைவாக காட்டு","search_holdings":"முதலீடுகளைத் தேடு","sort_by":"வரிசைப்படுத்து","current_value_sort":"தற்போதைய மதிப்பு","return_sort":"வருமான விகிதம்","name_sort":"பெயர்","avg_bought_price":"சராசரி வாங்கிய விலை","latest_price":"சமீபத்திய விலை","auto_market_price":"தானியங்கி சந்தை விலை","manual_fallback_price":"சந்தைத் தரவு இல்லாதபோது மட்டும் தற்போதைய விலை","market_price_help":"ஆதரிக்கப்படும் சந்தை விலைகளை SIGORA தானாகப் புதுப்பிக்கும். வாங்கிய விலை உங்கள் பதிவு செய்யப்பட்ட செலவுத் தளமாக மாறாமல் இருக்கும்.","price_delayed":"சந்தை விலைகள் தாமதமாகவோ தற்காலிகமாக கிடைக்காமலோ இருக்கலாம்.","last_price_sync":"கடைசி சந்தை ஒத்திசைவு","goal_connection":"இலக்கு இணைப்பு","goal_connection_sub":"சந்தை மதிப்பை உறுதியான இலக்கு நிதியாகக் கருதாமல், உங்கள் போர்ட்ஃபோலியோ உங்கள் இலக்குகளுடன் எப்படி ஒப்பிடப்படுகிறது என்பதைப் பாருங்கள்.","portfolio_equals_goal":"இந்த இலக்கு தொகையின் {pct}%க்கு போர்ட்ஃபோலியோ சமம்","no_goals_connect":"உங்கள் முதலீடுகளை ஒரு நோக்கத்துடன் இணைக்க இலக்கை உருவாக்குங்கள்.","portfolio_to_life":"போர்ட்ஃபோலியோ → வாழ்க்கை","portfolio_to_life_sub":"உங்கள் முதலீடுகள் உங்கள் முழு நிதிநிலைக்கு என்ன அர்த்தம் என்பதைப் பாருங்கள்.","of_net_worth_invested":"உங்கள் தற்போதைய நிகர சொத்து மதிப்பில் பதிவு செய்யப்பட்ட முதலீடுகள் குறிக்கும் பகுதி","largest_holding":"மிகப்பெரிய முதலீடு","emergency_cover":"அவசர நிதி பாதுகாப்பு","months_short":"மாதங்கள்","downside_20":"போர்ட்ஃபோலியோ 20% குறைந்தால்","net_worth_change":"மதிப்பிடப்பட்ட நிகர சொத்து மாற்றம்","scenario_lab":"சூழல் ஆய்வகம்","scenario_lab_sub":"கணித சூழல்களைப் பாருங்கள் — இது கணிப்பு அல்லது உறுதியான வருமான வாக்குறுதி அல்ல.","explore_scenarios":"சூழல்களை ஆராயுங்கள்","portfolio_drop":"போர்ட்ஃபோலியோ மாற்றம் %","estimated_portfolio":"மதிப்பிடப்பட்ட போர்ட்ஃபோலியோ மதிப்பு","estimated_net_worth":"மதிப்பிடப்பட்ட நிகர சொத்து மதிப்பு","apply_scenario":"சூழலைக் கணக்கிடு","holdings_count":"முதலீடுகள்","refresh_prices":"சந்தை விலைகளைப் புதுப்பி","prices_refreshed":"கிடைத்த சந்தை விலைகள் புதுப்பிக்கப்பட்டன.","price_refresh_partial":"சில சந்தை விலைகளை இப்போது புதுப்பிக்க முடியவில்லை.","add_holding":"முதலீட்டைச் சேர்","investment_name":"முதலீட்டு பெயர்","symbol_optional":"சின்னம் (விருப்பம்)","quantity":"அளவு","average_cost":"சராசரி வாங்கிய விலை","notes_optional":"குறிப்புகள் (விருப்பம்)","portfolio_value":"போர்ட்ஃபோலியோ மதிப்பு","gain_loss":"லாபம் / இழப்பு","market_unavailable":"சந்தைத் தரவு இல்லை","cost_basis":"செலவுத் தளம்","portfolio_share":"போர்ட்ஃபோலியோ பங்கு","remove_holding":"இந்த முதலீட்டை நீக்கவா?","no_holdings":"இன்னும் முதலீடுகள் இல்லை. உங்கள் முதல் முதலீட்டை மேலே சேர்க்கவும்.","goal_saved_amount":"இலக்குக்காக பதிவு செய்யப்பட்ட சேமிப்பு","goal_target":"இலக்கு தொகை","portfolio_reference":"போர்ட்ஃபோலியோ ஒப்பீடு","not_guaranteed":"உறுதியான நிதி அல்ல","portfolio_health_not_advice":"இந்த மதிப்பெண் பதிவு செய்யப்பட்ட தரவை மட்டுமே அடிப்படையாகக் கொண்ட கல்வி தகவல்; முதலீட்டு ஆலோசனை அல்ல.","price_source":"விலை மூலம்","market_data_may_be_delayed":"சந்தைத் தரவு தாமதமாக இருக்கலாம்"
},
"hi": {
"portfolio_intelligence":"पोर्टफोलियो इंटेलिजेंस","current_value":"मौजूदा मूल्य","today_change":"आज का बदलाव","tracked_return":"दर्ज रिटर्न","portfolio_health":"पोर्टफोलियो हेल्थ","portfolio_health_sub":"आपकी दर्ज होल्डिंग और वित्तीय संदर्भ से बने समझने योग्य संकेत।","your_holdings":"आपकी होल्डिंग्स","top_holdings":"मुख्य होल्डिंग्स","view_all_holdings":"सभी होल्डिंग्स देखें","hide_all_holdings":"कम होल्डिंग्स दिखाएँ","search_holdings":"होल्डिंग खोजें","sort_by":"क्रमबद्ध करें","current_value_sort":"मौजूदा मूल्य","return_sort":"रिटर्न","name_sort":"नाम","avg_bought_price":"औसत खरीदी कीमत","latest_price":"नवीनतम कीमत","auto_market_price":"ऑटो मार्केट कीमत","manual_fallback_price":"मार्केट डेटा न मिले तभी मौजूदा कीमत","market_price_help":"समर्थित मार्केट कीमतें SIGORA अपने आप अपडेट करता है। खरीदी कीमत आपकी दर्ज लागत बनी रहती है।","price_delayed":"मार्केट कीमतें देरी से मिल सकती हैं या अस्थायी रूप से उपलब्ध न हों।","last_price_sync":"आखिरी मार्केट सिंक","goal_connection":"लक्ष्य कनेक्शन","goal_connection_sub":"मार्केट मूल्य को गारंटीकृत लक्ष्य फंड माने बिना देखें कि आपका पोर्टफोलियो आपके लक्ष्यों से कैसे जुड़ता है।","portfolio_equals_goal":"पोर्टफोलियो इस लक्ष्य राशि के {pct}% के बराबर है","no_goals_connect":"अपने निवेशों को किसी उद्देश्य से जोड़ने के लिए एक लक्ष्य बनाएं।","portfolio_to_life":"पोर्टफोलियो → जीवन","portfolio_to_life_sub":"देखें कि आपके निवेश आपकी पूरी वित्तीय स्थिति के लिए क्या अर्थ रखते हैं।","of_net_worth_invested":"आपकी मौजूदा नेट वर्थ में दर्ज निवेशों का हिस्सा","largest_holding":"सबसे बड़ी होल्डिंग","emergency_cover":"आपातकालीन फंड कवरेज","months_short":"महीने","downside_20":"यदि पोर्टफोलियो 20% गिरता है","net_worth_change":"अनुमानित नेट-वर्थ बदलाव","scenario_lab":"सिनेरियो लैब","scenario_lab_sub":"गणितीय परिदृश्य देखें — यह पूर्वानुमान या वादा किया रिटर्न नहीं है।","explore_scenarios":"परिदृश्य देखें","portfolio_drop":"पोर्टफोलियो बदलाव %","estimated_portfolio":"अनुमानित पोर्टफोलियो मूल्य","estimated_net_worth":"अनुमानित नेट वर्थ","apply_scenario":"परिदृश्य गणना करें","holdings_count":"होल्डिंग्स","refresh_prices":"मार्केट कीमतें रिफ्रेश करें","prices_refreshed":"जहाँ उपलब्ध था वहाँ मार्केट कीमतें रिफ्रेश हो गईं।","price_refresh_partial":"कुछ मार्केट कीमतें अभी रिफ्रेश नहीं हो सकीं।","add_holding":"होल्डिंग जोड़ें","investment_name":"निवेश का नाम","symbol_optional":"सिंबल (वैकल्पिक)","quantity":"मात्रा","average_cost":"औसत लागत / खरीदी कीमत","notes_optional":"नोट्स (वैकल्पिक)","portfolio_value":"पोर्टफोलियो मूल्य","gain_loss":"लाभ / हानि","market_unavailable":"मार्केट उपलब्ध नहीं","cost_basis":"लागत आधार","portfolio_share":"पोर्टफोलियो हिस्सा","remove_holding":"इस होल्डिंग को हटाएँ?","no_holdings":"अभी कोई होल्डिंग नहीं है। ऊपर अपनी पहली होल्डिंग जोड़ें।","goal_saved_amount":"लक्ष्य के लिए दर्ज बचत","goal_target":"लक्ष्य","portfolio_reference":"पोर्टफोलियो संदर्भ","not_guaranteed":"गारंटीकृत फंड नहीं","portfolio_health_not_advice":"यह स्कोर केवल दर्ज डेटा पर आधारित शैक्षिक जानकारी है; निवेश सलाह नहीं है।","price_source":"कीमत स्रोत","market_data_may_be_delayed":"मार्केट डेटा में देरी हो सकती है"
}
}
for _lang, _items in _INVEST_V2_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)

_INVEST_V2_HEALTH_I18N = {
"en": {"health_not_enough":"Not enough data","health_strong":"Strong","health_balanced":"Balanced","health_attention":"Needs attention","health_concentration_risk":"High concentration risk","health_signal_very_high_concentration":"Very high single-holding concentration","health_signal_high_concentration":"High single-holding concentration","health_signal_moderate_concentration":"Moderate single-holding concentration","health_signal_controlled_concentration":"Single-holding concentration is controlled","health_signal_one_holding":"Only one holding is tracked","health_signal_limited_breadth":"Portfolio breadth is still limited","health_signal_multiple_holdings":"Multiple holdings are tracked","health_signal_one_asset_class":"Most value sits in one asset class","health_signal_low_emergency":"Emergency-fund coverage is below 3 months","health_signal_strong_emergency":"Emergency-fund coverage is 6+ months","market_price_missing":"Market price is unavailable for this holding. Enter a current price as a fallback."},
"ta": {"health_not_enough":"போதுமான தரவு இல்லை","health_strong":"வலுவானது","health_balanced":"சமநிலை","health_attention":"கவனம் தேவை","health_concentration_risk":"அதிக ஒருமுகப்படுத்தல் அபாயம்","health_signal_very_high_concentration":"ஒரே முதலீட்டில் மிக அதிக ஒருமுகப்படுத்தல்","health_signal_high_concentration":"ஒரே முதலீட்டில் அதிக ஒருமுகப்படுத்தல்","health_signal_moderate_concentration":"ஒரே முதலீட்டில் மிதமான ஒருமுகப்படுத்தல்","health_signal_controlled_concentration":"ஒரே முதலீட்டின் ஒருமுகப்படுத்தல் கட்டுப்பாட்டில் உள்ளது","health_signal_one_holding":"ஒரே ஒரு முதலீடு மட்டுமே பதிவு செய்யப்பட்டுள்ளது","health_signal_limited_breadth":"போர்ட்ஃபோலியோ பரவல் இன்னும் குறைவாக உள்ளது","health_signal_multiple_holdings":"பல முதலீடுகள் பதிவு செய்யப்பட்டுள்ளன","health_signal_one_asset_class":"பெரும்பாலான மதிப்பு ஒரே சொத்து வகையில் உள்ளது","health_signal_low_emergency":"அவசர நிதி பாதுகாப்பு 3 மாதங்களுக்கு குறைவாக உள்ளது","health_signal_strong_emergency":"அவசர நிதி பாதுகாப்பு 6+ மாதங்கள் உள்ளது","market_price_missing":"இந்த முதலீட்டிற்கான சந்தை விலை இப்போது கிடைக்கவில்லை. மாற்றாக தற்போதைய விலையை உள்ளிடுங்கள்."},
"hi": {"health_not_enough":"पर्याप्त डेटा नहीं","health_strong":"मजबूत","health_balanced":"संतुलित","health_attention":"ध्यान चाहिए","health_concentration_risk":"उच्च एकाग्रता जोखिम","health_signal_very_high_concentration":"एक ही होल्डिंग में बहुत अधिक एकाग्रता","health_signal_high_concentration":"एक ही होल्डिंग में अधिक एकाग्रता","health_signal_moderate_concentration":"एक ही होल्डिंग में मध्यम एकाग्रता","health_signal_controlled_concentration":"एक होल्डिंग की एकाग्रता नियंत्रित है","health_signal_one_holding":"केवल एक होल्डिंग दर्ज है","health_signal_limited_breadth":"पोर्टफोलियो का फैलाव अभी सीमित है","health_signal_multiple_holdings":"कई होल्डिंग्स दर्ज हैं","health_signal_one_asset_class":"अधिकांश मूल्य एक ही एसेट क्लास में है","health_signal_low_emergency":"आपातकालीन फंड कवरेज 3 महीने से कम है","health_signal_strong_emergency":"आपातकालीन फंड कवरेज 6+ महीने है","market_price_missing":"इस होल्डिंग की मार्केट कीमत अभी उपलब्ध नहीं है। विकल्प के रूप में मौजूदा कीमत दर्ज करें।"}
}
for _lang, _items in _INVEST_V2_HEALTH_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)


# Launch polish: complete visible Investments V2 / dashboard language coverage.
_LAUNCH_POLISH_I18N = {
"en": {
"invest_hero_sub":"Your money, beyond spending. Track investments, understand risk and connect your portfolio to your complete financial picture.",
"edit_profile":"Edit profile","build_risk_profile":"Build risk profile","ai_portfolio_insight":"AI portfolio insight","important":"Important","invest_disclaimer_full":"SIGORA provides educational analytics, portfolio tracking and risk information. It does not provide personalized buy/sell recommendations, target returns or guarantees.",
"start_here":"START HERE","investor_kind_title":"Tell SIGORA what kind of investor you are.","investor_kind_sub":"Answer a short risk-and-horizon questionnaire to unlock model allocation education and better portfolio warnings.","create_investor_profile":"Create investor profile","your_profile":"Your profile","horizon":"Horizon","years_short":"yrs","monthly_plan":"Monthly plan","invested_cost":"Invested cost",
"sigora_signal":"SIGORA SIGNAL","portfolio_life_label":"PORTFOLIO → LIFE","goals_investments_label":"GOALS × INVESTMENTS","goals_link":"Goals","portfolio_tracker_label":"PORTFOLIO TRACKER","sector_optional":"Sector (optional)","asset_stock":"Stock","asset_index_etf":"Index fund / ETF","asset_mutual_fund":"Mutual fund","asset_fixed_income":"Fixed income","asset_gold":"Gold","asset_cash_liquid":"Cash / liquid","asset_other":"Other","market_research":"Market research","remove":"Remove",
"attention":"ATTENTION","precautionary_signals":"Precautionary signals","diversification":"DIVERSIFICATION","what_you_own":"What you actually own","what_if":"WHAT IF?","starting_amount":"Starting amount","monthly_contribution":"Monthly contribution","years":"Years","assumed_annual_return":"Assumed annual return %","calculate_long_scenario":"Calculate long-term scenario","scenario_enter_assumptions":"Enter assumptions and calculate a scenario.","illustrative_ending_value":"Illustrative ending value",
"educational_model":"EDUCATIONAL MODEL","allocation_example":"{profile} allocation example","generic_learning_only":"This is a generic illustration for learning — not a recommendation for your money.","investment_explorer":"INVESTMENT EXPLORER","learn_before_choose":"Learn before you choose","asset_examples_not_picks":"These are asset-class examples, not personalized picks.","typical_learning_horizon":"Typical learning horizon","watchlist":"WATCHLIST","research_queue":"Research queue","watchlist_sub":"Type a company, ETF, fund or index name. SIGORA will resolve its market ticker automatically when market data is available.","watchlist_try":"Try Reliance, Apple, Microsoft, Nifty 50...","optional_research_note":"Optional research note","find_add":"Find & add","today":"today","market_unavailable_now":"Market data unavailable right now","view_chart":"View chart","watchlist_empty":"Your watchlist is empty.",
"warn_cashflow":"Your tracked expenses currently meet or exceed tracked income. Consider stabilising cash flow before increasing investment contributions.","warn_monthly_gt_surplus":"Your chosen monthly investment amount is higher than your tracked surplus. Review the amount before committing it.","warn_emergency_low":"Your entered emergency-fund coverage is below 3 months. Building liquidity may deserve attention before taking more market risk.","warn_asset_concentration":"{pct}% of your tracked portfolio is in {name}. High concentration can amplify losses as well as gains.","warn_sector_concentration":"{pct}% of your tracked portfolio is in the {name} sector.","warn_holding_concentration":"{name} is {pct}% of the tracked portfolio.",
"financial_overview":"Financial overview","personal_finance_label":"PERSONAL FINANCE","at_current_pace":"At your current recorded pace","detected_before_month_end":"Detected before month-end","no_budget_breach":"No projected budget breach detected","financial_momentum":"FINANCIAL MOMENTUM","level":"Level","day_streak":"day streak","best":"best","first_transaction":"First transaction","first_move":"First move","consistent":"Consistent","budget_builder":"Budget builder","goal_setter":"Goal setter","goal_achiever":"Goal achiever","smart_alerts":"SMART ALERTS","things_worth_seeing":"Things worth seeing","active":"active","open":"Open",
"headline_strong_momentum":"Your recorded finances are showing strong momentum."
},
"ta": {
"invest_hero_sub":"செலவைத் தாண்டி உங்கள் பணத்தைப் பாருங்கள். முதலீடுகளை கண்காணித்து, அபாயத்தைப் புரிந்து, உங்கள் முழு நிதிநிலையுடன் போர்ட்ஃபோலியோவை இணைக்கவும்.",
"edit_profile":"சுயவிவரத்தைத் திருத்து","build_risk_profile":"அபாய சுயவிவரத்தை உருவாக்கு","ai_portfolio_insight":"AI போர்ட்ஃபோலியோ விளக்கம்","important":"முக்கியம்","invest_disclaimer_full":"SIGORA கல்வி பகுப்பாய்வு, போர்ட்ஃபோலியோ கண்காணிப்பு மற்றும் அபாயத் தகவலை வழங்குகிறது. தனிப்பட்ட வாங்க/விற்க பரிந்துரைகள், இலக்கு வருமானம் அல்லது உத்தரவாதங்களை வழங்காது.",
"start_here":"இங்கிருந்து தொடங்கு","investor_kind_title":"நீங்கள் எந்த வகை முதலீட்டாளர் என்பதை SIGORA-க்கு சொல்லுங்கள்.","investor_kind_sub":"மாதிரி சொத்து ஒதுக்கீட்டு கல்வி மற்றும் சிறந்த போர்ட்ஃபோலியோ எச்சரிக்கைகளைப் பெற சுருக்கமான அபாய-கால அளவு கேள்விகளுக்கு பதிலளிக்கவும்.","create_investor_profile":"முதலீட்டாளர் சுயவிவரத்தை உருவாக்கு","your_profile":"உங்கள் சுயவிவரம்","horizon":"கால அளவு","years_short":"ஆண்டுகள்","monthly_plan":"மாத திட்டம்","invested_cost":"முதலீட்டுச் செலவு",
"sigora_signal":"SIGORA சிக்னல்","portfolio_life_label":"போர்ட்ஃபோலியோ → வாழ்க்கை","goals_investments_label":"இலக்குகள் × முதலீடுகள்","goals_link":"இலக்குகள்","portfolio_tracker_label":"போர்ட்ஃபோலியோ கண்காணிப்பு","sector_optional":"துறை (விருப்பம்)","asset_stock":"பங்கு","asset_index_etf":"குறியீட்டு நிதி / ETF","asset_mutual_fund":"மியூச்சுவல் ஃபண்ட்","asset_fixed_income":"நிலையான வருமானம்","asset_gold":"தங்கம்","asset_cash_liquid":"பணம் / திரவ நிதி","asset_other":"மற்றவை","market_research":"சந்தை ஆய்வு","remove":"நீக்கு",
"attention":"கவனம்","precautionary_signals":"முன்னெச்சரிக்கை சிக்னல்கள்","diversification":"பரவலாக்கம்","what_you_own":"நீங்கள் உண்மையில் வைத்திருப்பது","what_if":"என்ன ஆகும்?","starting_amount":"தொடக்கத் தொகை","monthly_contribution":"மாதாந்திர பங்களிப்பு","years":"ஆண்டுகள்","assumed_annual_return":"கருதப்பட்ட ஆண்டு வருமானம் %","calculate_long_scenario":"நீண்டகால சூழலைக் கணக்கிடு","scenario_enter_assumptions":"கருதுகோள்களை உள்ளிட்டு ஒரு சூழலைக் கணக்கிடுங்கள்.","illustrative_ending_value":"உதாரண இறுதி மதிப்பு",
"educational_model":"கல்வி மாதிரி","allocation_example":"{profile} சொத்து ஒதுக்கீட்டு உதாரணம்","generic_learning_only":"இது கற்றலுக்கான பொதுவான உதாரணம் மட்டுமே — உங்கள் பணத்திற்கான பரிந்துரை அல்ல.","investment_explorer":"முதலீட்டு ஆராய்ச்சி","learn_before_choose":"தேர்வு செய்வதற்கு முன் கற்றுக்கொள்ளுங்கள்","asset_examples_not_picks":"இவை சொத்து வகை உதாரணங்கள்; தனிப்பட்ட பரிந்துரைகள் அல்ல.","typical_learning_horizon":"வழக்கமான கற்றல் கால அளவு","watchlist":"கவனிப்பு பட்டியல்","research_queue":"ஆய்வு பட்டியல்","watchlist_sub":"நிறுவனம், ETF, நிதி அல்லது குறியீட்டு பெயரை உள்ளிடுங்கள். சந்தைத் தரவு கிடைத்தால் SIGORA அதன் டிக்கரை தானாக கண்டறியும்.","watchlist_try":"Reliance, Apple, Microsoft, Nifty 50 போன்றவற்றை முயற்சிக்கவும்...","optional_research_note":"விருப்ப ஆய்வு குறிப்பு","find_add":"கண்டறிந்து சேர்","today":"இன்று","market_unavailable_now":"சந்தைத் தரவு இப்போது கிடைக்கவில்லை","view_chart":"வரைபடத்தைப் பார்","watchlist_empty":"உங்கள் கவனிப்பு பட்டியல் காலியாக உள்ளது.",
"warn_cashflow":"உங்கள் பதிவு செய்யப்பட்ட செலவுகள் தற்போது பதிவு செய்யப்பட்ட வருமானத்துக்கு சமமாகவோ அதிகமாகவோ உள்ளன. முதலீட்டு பங்களிப்பை அதிகரிக்கும் முன் பணப்புழக்கத்தை நிலைப்படுத்துவது நல்லது.","warn_monthly_gt_surplus":"நீங்கள் தேர்ந்தெடுத்த மாதாந்திர முதலீட்டு தொகை பதிவு செய்யப்பட்ட மீதத் தொகையை விட அதிகமாக உள்ளது. உறுதி செய்வதற்கு முன் தொகையை மறுபரிசீலனை செய்யுங்கள்.","warn_emergency_low":"நீங்கள் பதிவு செய்த அவசர நிதி பாதுகாப்பு 3 மாதங்களுக்கு குறைவாக உள்ளது. கூடுதல் சந்தை அபாயத்தை ஏற்கும் முன் திரவ நிதியை அதிகரிப்பது கவனிக்கத் தக்கது.","warn_asset_concentration":"உங்கள் பதிவு செய்யப்பட்ட போர்ட்ஃபோலியோவில் {pct}% {name}-ல் உள்ளது. அதிக ஒருமுகப்படுத்தல் லாபத்தையும் இழப்பையும் அதிகப்படுத்தலாம்.","warn_sector_concentration":"உங்கள் பதிவு செய்யப்பட்ட போர்ட்ஃபோலியோவில் {pct}% {name} துறையில் உள்ளது.","warn_holding_concentration":"{name} பதிவு செய்யப்பட்ட போர்ட்ஃபோலியோவில் {pct}% ஆக உள்ளது.",
"financial_overview":"நிதி மேலோட்டம்","personal_finance_label":"தனிநபர் நிதி","at_current_pace":"உங்கள் தற்போதைய பதிவு செய்யப்பட்ட வேகத்தில்","detected_before_month_end":"மாத இறுதிக்கு முன் கண்டறியப்பட்டது","no_budget_breach":"கணிக்கப்பட்ட பட்ஜெட் மீறல் இல்லை","financial_momentum":"நிதி முன்னேற்றம்","level":"நிலை","day_streak":"நாள் தொடர்ச்சி","best":"சிறந்தது","first_transaction":"முதல் பரிவர்த்தனை","first_move":"முதல் முன்னேற்றம்","consistent":"தொடர்ச்சி","budget_builder":"பட்ஜெட் உருவாக்குபவர்","goal_setter":"இலக்கு அமைப்பவர்","goal_achiever":"இலக்கு சாதிப்பவர்","smart_alerts":"ஸ்மார்ட் எச்சரிக்கைகள்","things_worth_seeing":"கவனிக்க வேண்டியவை","active":"செயலில்","open":"திற",
"headline_strong_momentum":"உங்கள் பதிவு செய்யப்பட்ட நிதிநிலை வலுவான முன்னேற்றத்தை காட்டுகிறது."
},
"hi": {
"invest_hero_sub":"खर्च से आगे अपने पैसे को समझें। निवेश ट्रैक करें, जोखिम समझें और पोर्टफोलियो को अपनी पूरी वित्तीय स्थिति से जोड़ें।",
"edit_profile":"प्रोफ़ाइल संपादित करें","build_risk_profile":"जोखिम प्रोफ़ाइल बनाएं","ai_portfolio_insight":"AI पोर्टफोलियो व्याख्या","important":"महत्वपूर्ण","invest_disclaimer_full":"SIGORA शैक्षिक विश्लेषण, पोर्टफोलियो ट्रैकिंग और जोखिम जानकारी देता है। यह व्यक्तिगत खरीद/बिक्री सलाह, लक्ष्य रिटर्न या गारंटी नहीं देता।",
"start_here":"यहाँ से शुरू करें","investor_kind_title":"SIGORA को बताएं कि आप किस तरह के निवेशक हैं।","investor_kind_sub":"मॉडल एसेट-एलोकेशन शिक्षा और बेहतर पोर्टफोलियो चेतावनियों के लिए छोटा जोखिम और समय-सीमा प्रश्नावली पूरा करें।","create_investor_profile":"निवेशक प्रोफ़ाइल बनाएं","your_profile":"आपकी प्रोफ़ाइल","horizon":"समय-सीमा","years_short":"वर्ष","monthly_plan":"मासिक योजना","invested_cost":"निवेशित लागत",
"sigora_signal":"SIGORA संकेत","portfolio_life_label":"पोर्टफोलियो → जीवन","goals_investments_label":"लक्ष्य × निवेश","goals_link":"लक्ष्य","portfolio_tracker_label":"पोर्टफोलियो ट्रैकर","sector_optional":"सेक्टर (वैकल्पिक)","asset_stock":"स्टॉक","asset_index_etf":"इंडेक्स फंड / ETF","asset_mutual_fund":"म्यूचुअल फंड","asset_fixed_income":"फिक्स्ड इनकम","asset_gold":"सोना","asset_cash_liquid":"नकद / लिक्विड","asset_other":"अन्य","market_research":"मार्केट रिसर्च","remove":"हटाएँ",
"attention":"ध्यान","precautionary_signals":"सावधानी संकेत","diversification":"विविधीकरण","what_you_own":"आप वास्तव में क्या रखते हैं","what_if":"क्या हो अगर?","starting_amount":"शुरुआती राशि","monthly_contribution":"मासिक योगदान","years":"वर्ष","assumed_annual_return":"मान लिया वार्षिक रिटर्न %","calculate_long_scenario":"दीर्घकालीन परिदृश्य गणना करें","scenario_enter_assumptions":"मान्यताएँ दर्ज करके परिदृश्य गणना करें।","illustrative_ending_value":"उदाहरणात्मक अंतिम मूल्य",
"educational_model":"शैक्षिक मॉडल","allocation_example":"{profile} एलोकेशन उदाहरण","generic_learning_only":"यह सीखने के लिए सामान्य उदाहरण है — आपके पैसे के लिए सलाह नहीं।","investment_explorer":"निवेश एक्सप्लोरर","learn_before_choose":"चुनने से पहले सीखें","asset_examples_not_picks":"ये एसेट-क्लास उदाहरण हैं, व्यक्तिगत चयन नहीं।","typical_learning_horizon":"सामान्य सीखने की अवधि","watchlist":"वॉचलिस्ट","research_queue":"रिसर्च कतार","watchlist_sub":"कंपनी, ETF, फंड या इंडेक्स का नाम लिखें। मार्केट डेटा मिलने पर SIGORA उसका टिकर अपने आप खोजेगा।","watchlist_try":"Reliance, Apple, Microsoft, Nifty 50 आज़माएँ...","optional_research_note":"वैकल्पिक रिसर्च नोट","find_add":"खोजें और जोड़ें","today":"आज","market_unavailable_now":"मार्केट डेटा अभी उपलब्ध नहीं है","view_chart":"चार्ट देखें","watchlist_empty":"आपकी वॉचलिस्ट खाली है।",
"warn_cashflow":"आपके दर्ज खर्च अभी दर्ज आय के बराबर या अधिक हैं। निवेश योगदान बढ़ाने से पहले कैश फ्लो को स्थिर करने पर विचार करें।","warn_monthly_gt_surplus":"आपकी चुनी मासिक निवेश राशि दर्ज अधिशेष से अधिक है। प्रतिबद्ध होने से पहले राशि की समीक्षा करें।","warn_emergency_low":"आपका दर्ज आपातकालीन फंड कवरेज 3 महीने से कम है। अधिक मार्केट जोखिम लेने से पहले नकदी उपलब्धता बढ़ाने पर ध्यान दें।","warn_asset_concentration":"आपके दर्ज पोर्टफोलियो का {pct}% {name} में है। अधिक एकाग्रता लाभ और हानि दोनों बढ़ा सकती है।","warn_sector_concentration":"आपके दर्ज पोर्टफोलियो का {pct}% {name} सेक्टर में है।","warn_holding_concentration":"{name} दर्ज पोर्टफोलियो का {pct}% है।",
"financial_overview":"वित्तीय अवलोकन","personal_finance_label":"पर्सनल फाइनेंस","at_current_pace":"आपकी मौजूदा दर्ज गति पर","detected_before_month_end":"महीने के अंत से पहले पहचाना गया","no_budget_breach":"कोई अनुमानित बजट उल्लंघन नहीं","financial_momentum":"वित्तीय गति","level":"लेवल","day_streak":"दिन की स्ट्रीक","best":"सर्वश्रेष्ठ","first_transaction":"पहला लेन-देन","first_move":"पहला कदम","consistent":"निरंतर","budget_builder":"बजट बिल्डर","goal_setter":"लक्ष्य बनाने वाला","goal_achiever":"लक्ष्य हासिल करने वाला","smart_alerts":"स्मार्ट अलर्ट","things_worth_seeing":"ध्यान देने योग्य बातें","active":"सक्रिय","open":"खोलें",
"headline_strong_momentum":"आपकी दर्ज वित्तीय स्थिति मजबूत गति दिखा रही है।"
}
}
for _lang, _items in _LAUNCH_POLISH_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)

_DASHBOARD_AI_I18N = {
"en": {"insight_label":"INSIGHT","recommended_next_step":"Recommended next step","focus_area":"Focus area","biggest_expense_category":"Biggest expense category","no_expense_category":"No expense category yet","dash_ai_empty_title":"Your financial picture starts here.","dash_ai_empty_body":"Add a few transactions and SIGORA will start turning your financial activity into useful patterns, spending signals and insights.","dash_ai_negative_title":"Your current spending is ahead of your income.","dash_ai_negative_body":"You've recorded {expense} in expenses against {income} in income. Review your spending categories and identify areas where you can cut unnecessary spending.","dash_ai_high_spend_title":"You're doing okay, but your spending deserves attention.","dash_ai_high_spend_body":"Around {pct}% of your recorded income has already been spent. Keeping an eye on your biggest categories could help protect your remaining balance.","dash_ai_healthy_title":"Your finances are currently in a healthy position.","dash_ai_healthy_body":"You've recorded {income} in income and {expense} in expenses, leaving you with {balance} in recorded balance. Keep tracking consistently to make this picture even more useful.","start_tracking_transactions":"Start tracking your transactions","reduce_spending":"Reduce spending","watch_spending":"Watch your spending"},
"ta": {"insight_label":"நுண்ணறிவு","recommended_next_step":"பரிந்துரைக்கப்படும் அடுத்த படி","focus_area":"கவனம் செலுத்த வேண்டியது","biggest_expense_category":"மிகப்பெரிய செலவுப் பிரிவு","no_expense_category":"இன்னும் செலவுப் பிரிவு இல்லை","dash_ai_empty_title":"உங்கள் நிதிப் படம் இங்கிருந்து தொடங்குகிறது.","dash_ai_empty_body":"சில பரிவர்த்தனைகளைச் சேர்த்தால், உங்கள் நிதிச் செயல்பாட்டை பயனுள்ள முறைகள், செலவு சிக்னல்கள் மற்றும் நுண்ணறிவுகளாக SIGORA மாற்றத் தொடங்கும்.","dash_ai_negative_title":"உங்கள் தற்போதைய செலவு உங்கள் வருமானத்தை விட முன்னிலையில் உள்ளது.","dash_ai_negative_body":"வருமானம் {income}க்கு எதிராக {expense} செலவாக பதிவு செய்துள்ளீர்கள். உங்கள் செலவுப் பிரிவுகளைப் பார்த்து தேவையற்ற செலவை குறைக்கக்கூடிய இடங்களை கண்டறியுங்கள்.","dash_ai_high_spend_title":"நிலை சரியாக உள்ளது, ஆனால் உங்கள் செலவு கவனம் தேவைப்படுகிறது.","dash_ai_high_spend_body":"உங்கள் பதிவு செய்யப்பட்ட வருமானத்தின் சுமார் {pct}% ஏற்கனவே செலவாகியுள்ளது. மிகப்பெரிய செலவுப் பிரிவுகளை கவனிப்பது மீதமுள்ள இருப்பை பாதுகாக்க உதவும்.","dash_ai_healthy_title":"உங்கள் நிதிநிலை தற்போது ஆரோக்கியமான நிலையில் உள்ளது.","dash_ai_healthy_body":"{income} வருமானமும் {expense} செலவும் பதிவு செய்துள்ளீர்கள்; பதிவு செய்யப்பட்ட மீதம் {balance}. தொடர்ந்து கண்காணிப்பது இந்தப் படத்தை மேலும் பயனுள்ளதாக மாற்றும்.","start_tracking_transactions":"உங்கள் பரிவர்த்தனைகளை கண்காணிக்கத் தொடங்குங்கள்","reduce_spending":"செலவை குறைக்கவும்","watch_spending":"உங்கள் செலவை கவனிக்கவும்"},
"hi": {"insight_label":"इनसाइट","recommended_next_step":"सुझाया अगला कदम","focus_area":"ध्यान का क्षेत्र","biggest_expense_category":"सबसे बड़ा खर्च वर्ग","no_expense_category":"अभी कोई खर्च वर्ग नहीं","dash_ai_empty_title":"आपकी वित्तीय तस्वीर यहाँ से शुरू होती है।","dash_ai_empty_body":"कुछ लेन-देन जोड़ें और SIGORA आपकी वित्तीय गतिविधि को उपयोगी पैटर्न, खर्च संकेत और इनसाइट में बदलना शुरू करेगा।","dash_ai_negative_title":"आपका मौजूदा खर्च आपकी आय से आगे है।","dash_ai_negative_body":"आपने {income} आय के मुकाबले {expense} खर्च दर्ज किया है। अपने खर्च वर्गों की समीक्षा करें और अनावश्यक खर्च घटाने के अवसर खोजें।","dash_ai_high_spend_title":"स्थिति ठीक है, लेकिन आपके खर्च पर ध्यान देना चाहिए।","dash_ai_high_spend_body":"आपकी दर्ज आय का लगभग {pct}% पहले ही खर्च हो चुका है। सबसे बड़े खर्च वर्गों पर नज़र रखना शेष बैलेंस बचाने में मदद कर सकता है।","dash_ai_healthy_title":"आपकी वित्तीय स्थिति अभी स्वस्थ है।","dash_ai_healthy_body":"आपने {income} आय और {expense} खर्च दर्ज किया है, जिससे {balance} दर्ज बैलेंस बचता है। लगातार ट्रैक करते रहें ताकि यह तस्वीर और उपयोगी बने।","start_tracking_transactions":"अपने लेन-देन ट्रैक करना शुरू करें","reduce_spending":"खर्च कम करें","watch_spending":"खर्च पर नज़र रखें"}
}
for _lang, _items in _DASHBOARD_AI_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)

_EXPLORER_PHRASES = {
"ta": {
"Broad-market equity":"பரந்த சந்தை பங்குகள்","Broader equity":"மேலும் பரந்த பங்குச் சந்தை","Government fixed income":"அரசு நிலையான வருமானம்","Bank deposits":"வங்கி வைப்பு","Gold":"தங்கம்","Individual equities":"தனிநபர் பங்குகள்","Nifty 50 / Sensex index funds or ETFs":"Nifty 50 / Sensex குறியீட்டு நிதிகள் அல்லது ETF-கள்","Nifty 500 / total-market style index funds":"Nifty 500 / மொத்த சந்தை வகை குறியீட்டு நிதிகள்","Treasury bills / government securities":"Treasury bills / அரசு பத்திரங்கள்","FD / RD from regulated banks":"ஒழுங்குபடுத்தப்பட்ட வங்கிகளின் FD / RD","Gold ETF / eligible regulated gold products":"Gold ETF / தகுதியான ஒழுங்குபடுத்தப்பட்ட தங்க தயாரிப்புகள்","Listed companies across banking, IT, consumer, industrial and other sectors":"வங்கி, IT, நுகர்வோர், தொழில் மற்றும் பிற துறைகளில் பட்டியலிடப்பட்ட நிறுவனங்கள்","Diversified exposure to large Indian companies.":"பெரிய இந்திய நிறுவனங்களில் பரவலான முதலீட்டு வெளிப்பாடு.","Wider equity diversification across market segments.":"சந்தையின் பல பிரிவுகளிலும் விரிவான பங்கு பரவலாக்கம்.","Lower-volatility fixed-income exposure; values can still move with interest rates.":"குறைந்த ஏற்றத் தாழ்வுள்ள நிலையான வருமான வெளிப்பாடு; வட்டி விகிதங்களால் மதிப்பு மாறலாம்.","Capital stability and predictable interest, subject to institution/tenure terms.":"நிறுவனம் மற்றும் காலநிலை விதிகளுக்கு உட்பட்டு முதல்தொகை நிலைத்தன்மை மற்றும் கணிக்கக்கூடிய வட்டி.","Diversifier; prices can be volatile and do not generate business cash flows.":"பரவலாக்க உதவும்; விலைகள் ஏற்றத் தாழ்வாக இருக்கலாம் மற்றும் வணிக பணப்புழக்கத்தை உருவாக்காது.","Company-specific exposure requiring deeper research and diversification.":"ஆழமான ஆய்வும் பரவலாக்கமும் தேவைப்படும் நிறுவனம் சார்ந்த முதலீட்டு வெளிப்பாடு.","High":"அதிகம்","Low–Moderate":"குறைவு–மிதம்","Low":"குறைவு","Moderate":"மிதம்","5+ years":"5+ ஆண்டுகள்","7+ years":"7+ ஆண்டுகள்","Months to years":"மாதங்கள் முதல் ஆண்டுகள் வரை","Defined tenure":"நிர்ணயிக்கப்பட்ட காலம்","3+ years":"3+ ஆண்டுகள்"},
"hi": {
"Broad-market equity":"व्यापक बाज़ार इक्विटी","Broader equity":"और व्यापक इक्विटी","Government fixed income":"सरकारी फिक्स्ड इनकम","Bank deposits":"बैंक जमा","Gold":"सोना","Individual equities":"व्यक्तिगत शेयर","Nifty 50 / Sensex index funds or ETFs":"Nifty 50 / Sensex इंडेक्स फंड या ETF","Nifty 500 / total-market style index funds":"Nifty 500 / कुल-बाज़ार शैली इंडेक्स फंड","Treasury bills / government securities":"ट्रेज़री बिल / सरकारी प्रतिभूतियाँ","FD / RD from regulated banks":"विनियमित बैंकों की FD / RD","Gold ETF / eligible regulated gold products":"Gold ETF / पात्र विनियमित गोल्ड उत्पाद","Listed companies across banking, IT, consumer, industrial and other sectors":"बैंकिंग, IT, उपभोक्ता, औद्योगिक और अन्य क्षेत्रों की सूचीबद्ध कंपनियाँ","Diversified exposure to large Indian companies.":"बड़ी भारतीय कंपनियों में विविध एक्सपोज़र।","Wider equity diversification across market segments.":"बाज़ार के विभिन्न हिस्सों में अधिक व्यापक इक्विटी विविधीकरण।","Lower-volatility fixed-income exposure; values can still move with interest rates.":"कम उतार-चढ़ाव वाला फिक्स्ड-इनकम एक्सपोज़र; ब्याज दरों के साथ मूल्य बदल सकता है।","Capital stability and predictable interest, subject to institution/tenure terms.":"संस्था और अवधि की शर्तों के अधीन पूंजी स्थिरता और अपेक्षाकृत पूर्वानुमेय ब्याज।","Diversifier; prices can be volatile and do not generate business cash flows.":"विविधीकरण में मदद करता है; कीमतें अस्थिर हो सकती हैं और व्यावसायिक कैश फ्लो पैदा नहीं करतीं।","Company-specific exposure requiring deeper research and diversification.":"कंपनी-विशिष्ट एक्सपोज़र जिसमें अधिक रिसर्च और विविधीकरण चाहिए।","High":"उच्च","Low–Moderate":"कम–मध्यम","Low":"कम","Moderate":"मध्यम","5+ years":"5+ वर्ष","7+ years":"7+ वर्ष","Months to years":"महीनों से वर्षों तक","Defined tenure":"निर्धारित अवधि","3+ years":"3+ वर्ष"}
}
for _lang, _items in _EXPLORER_PHRASES.items():
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {}).update(_items)

_MONEY_MODEL_I18N = {
"en": {"cash_bank":"Cash & Bank","tracked_cash_v2":"Bank accounts, physical cash and stored wallets","cash_not_setup":"Not set up","cash_not_setup_help":"Add a current bank, cash or wallet balance for accurate net-worth tracking.","money_movement":"MONEY MOVEMENT","add_transaction":"Add transaction","record_once":"Record what happened and where the money moved.","transaction_type":"Transaction type","income":"Income","expense":"Expense","transfer":"Transfer","paid_from":"Paid from","received_into":"Received into","not_linked":"Not linked to an account","physical_cash":"Physical Cash","physical_cash_first":"Current physical cash balance","physical_cash_first_help":"Only needed the first time you use Physical Cash. This becomes the starting checkpoint.","from_account":"From account","to_account":"To account","transfer_help":"Transfers move your own money and never count as income or spending.","amount_positive":"Amount must be greater than 0.","description_required":"Description cannot be empty.","valid_date_required":"Please enter a valid date.","transfer_accounts_required":"Choose both the source and destination accounts.","valid_transaction_type":"Choose a valid transaction type.","choose_valid_account":"Choose a valid account.","cash_wallets":"Cash & wallets","physical_cash_desc":"Money you physically have. It does not need to have come from a bank.","digital_wallet":"Digital wallet","wallet_desc":"Stored-value balance such as Amazon Pay Wallet. Do not add UPI apps that spend directly from your bank account.","bank_accounts":"Bank accounts","credit_debt":"Credit & debt","your_bank_login_stays":"Your bank login stays with you","privacy_notice":"SIGORA does not ask for or collect your bank username, password, PIN, CVV or OTP. Manual accounts and statement imports use only the financial information you choose to provide. SIGORA does not log in to your bank on your behalf.","never_share_credentials":"Never enter your banking password, PIN, CVV or OTP anywhere in SIGORA.","import_confidence":"Import with confidence","import_privacy":"Uploading a statement does not give SIGORA access to your bank account. SIGORA only processes the statement you choose to provide.","source_account":"Account / source","import_review_note":"Review SIGORA's interpretation before saving. Uncertain rows are never silently invented.","account":"Account","unassigned":"Unassigned","transfer_detected":"Transfer-like movement","transaction_source":"Source","cash_account":"Physical cash","wallet_only_after_add":"Wallets appear in transactions only after you add them here."},
"ta": {"cash_bank":"பணம் & வங்கி","tracked_cash_v2":"வங்கி கணக்குகள், கையிருப்பு பணம் மற்றும் சேமிக்கப்பட்ட வாலெட்டுகள்","cash_not_setup":"அமைக்கப்படவில்லை","cash_not_setup_help":"துல்லியமான நிகர சொத்து கணக்கிற்கு தற்போதைய வங்கி, பணம் அல்லது வாலெட் இருப்பைச் சேர்க்கவும்.","money_movement":"பண இயக்கம்","add_transaction":"பரிவர்த்தனையைச் சேர்","record_once":"என்ன நடந்தது, பணம் எங்கு நகர்ந்தது என்பதை பதிவு செய்யுங்கள்.","transaction_type":"பரிவர்த்தனை வகை","income":"வருமானம்","expense":"செலவு","transfer":"பரிமாற்றம்","paid_from":"எதிலிருந்து செலுத்தப்பட்டது","received_into":"எதில் பெறப்பட்டது","not_linked":"கணக்குடன் இணைக்கப்படவில்லை","physical_cash":"கையிருப்பு பணம்","physical_cash_first":"தற்போதைய கையிருப்பு பணம்","physical_cash_first_help":"கையிருப்பு பணத்தை முதல் முறை பயன்படுத்தும்போது மட்டும் தேவை. இது தொடக்க இருப்பாகும்.","from_account":"எந்த கணக்கிலிருந்து","to_account":"எந்த கணக்கிற்கு","transfer_help":"உங்கள் சொந்த கணக்குகளுக்கிடையிலான பரிமாற்றம் வருமானம் அல்லது செலவாக கணக்கிடப்படாது.","amount_positive":"தொகை 0-ஐ விட அதிகமாக இருக்க வேண்டும்.","description_required":"விவரம் காலியாக இருக்கக்கூடாது.","valid_date_required":"சரியான தேதியை உள்ளிடவும்.","transfer_accounts_required":"மூலமும் இலக்கும் ஆகிய இரு கணக்குகளையும் தேர்வு செய்யவும்.","valid_transaction_type":"சரியான பரிவர்த்தனை வகையைத் தேர்வு செய்யவும்.","choose_valid_account":"சரியான கணக்கைத் தேர்வு செய்யவும்.","cash_wallets":"பணம் & வாலெட்டுகள்","physical_cash_desc":"உங்களிடம் நேரடியாக உள்ள பணம். அது வங்கியில் இருந்து வந்திருக்க வேண்டிய அவசியமில்லை.","digital_wallet":"டிஜிட்டல் வாலெட்","wallet_desc":"Amazon Pay Wallet போன்ற சேமிக்கப்பட்ட வாலெட் இருப்பு. வங்கி கணக்கிலிருந்து நேரடியாக செலவிடும் UPI செயலிகளை தனியாக சேர்க்க வேண்டாம்.","bank_accounts":"வங்கி கணக்குகள்","credit_debt":"கிரெடிட் & கடன்","your_bank_login_stays":"உங்கள் வங்கி உள்நுழைவு தகவல் உங்களிடமே இருக்கும்","privacy_notice":"SIGORA உங்கள் வங்கி பயனர்பெயர், கடவுச்சொல், PIN, CVV அல்லது OTP-ஐ கேட்கவோ சேகரிக்கவோாது. கைமுறை கணக்குகள் மற்றும் அறிக்கை இறக்குமதிகளில் நீங்கள் வழங்கும் நிதித் தகவல் மட்டுமே பயன்படுத்தப்படும். SIGORA உங்கள் சார்பில் வங்கியில் உள்நுழையாது.","never_share_credentials":"உங்கள் வங்கி கடவுச்சொல், PIN, CVV அல்லது OTP-ஐ SIGORA-வில் எங்கும் உள்ளிட வேண்டாம்.","import_confidence":"நம்பிக்கையுடன் இறக்குமதி செய்யுங்கள்","import_privacy":"அறிக்கையை பதிவேற்றுவது SIGORA-க்கு உங்கள் வங்கி கணக்கை அணுக அனுமதி அளிக்காது. நீங்கள் வழங்கும் அறிக்கையை மட்டுமே SIGORA செயலாக்கும்.","source_account":"கணக்கு / மூலம்","import_review_note":"சேமிப்பதற்கு முன் SIGORA-வின் விளக்கத்தை சரிபார்க்கவும். தெளிவில்லாத தகவல் அமைதியாக உருவாக்கப்படாது.","account":"கணக்கு","unassigned":"இணைக்கப்படாதது","transfer_detected":"பரிமாற்றம் போன்ற இயக்கம்","transaction_source":"மூலம்","cash_account":"கையிருப்பு பணம்","wallet_only_after_add":"வாலெட்டை இங்கே சேர்த்த பிறகே அது பரிவர்த்தனைகளில் தோன்றும்."},
"hi": {"cash_bank":"कैश और बैंक","tracked_cash_v2":"बैंक खाते, भौतिक नकद और स्टोर्ड वॉलेट","cash_not_setup":"सेट अप नहीं","cash_not_setup_help":"सटीक नेट वर्थ के लिए मौजूदा बैंक, नकद या वॉलेट बैलेंस जोड़ें।","money_movement":"पैसे की आवाजाही","add_transaction":"लेन-देन जोड़ें","record_once":"क्या हुआ और पैसा कहां गया या आया, उसे दर्ज करें।","transaction_type":"लेन-देन का प्रकार","income":"आय","expense":"खर्च","transfer":"ट्रांसफर","paid_from":"कहां से भुगतान हुआ","received_into":"कहां प्राप्त हुआ","not_linked":"किसी खाते से लिंक नहीं","physical_cash":"भौतिक नकद","physical_cash_first":"मौजूदा भौतिक नकद बैलेंस","physical_cash_first_help":"भौतिक नकद पहली बार उपयोग करते समय ही जरूरी। यह शुरुआती बैलेंस चेकपॉइंट बनेगा।","from_account":"किस खाते से","to_account":"किस खाते में","transfer_help":"अपने खातों के बीच ट्रांसफर आय या खर्च में नहीं गिने जाते।","amount_positive":"राशि 0 से अधिक होनी चाहिए।","description_required":"विवरण खाली नहीं हो सकता।","valid_date_required":"कृपया सही तारीख दर्ज करें।","transfer_accounts_required":"स्रोत और गंतव्य दोनों खाते चुनें।","valid_transaction_type":"सही लेन-देन प्रकार चुनें।","choose_valid_account":"सही खाता चुनें।","cash_wallets":"कैश और वॉलेट","physical_cash_desc":"आपके पास मौजूद भौतिक नकद। इसका बैंक से आया होना जरूरी नहीं है।","digital_wallet":"डिजिटल वॉलेट","wallet_desc":"Amazon Pay Wallet जैसा स्टोर्ड-वैल्यू बैलेंस। बैंक खाते से सीधे खर्च करने वाले UPI ऐप को अलग बैलेंस के रूप में न जोड़ें।","bank_accounts":"बैंक खाते","credit_debt":"क्रेडिट और कर्ज","your_bank_login_stays":"आपका बैंक लॉगिन आपके पास ही रहता है","privacy_notice":"SIGORA आपका बैंक यूज़रनेम, पासवर्ड, PIN, CVV या OTP नहीं मांगता या इकट्ठा नहीं करता। मैनुअल खाते और स्टेटमेंट इम्पोर्ट में केवल वही वित्तीय जानकारी उपयोग होती है जो आप देना चुनते हैं। SIGORA आपकी ओर से बैंक में लॉग इन नहीं करता।","never_share_credentials":"अपना बैंक पासवर्ड, PIN, CVV या OTP SIGORA में कहीं भी दर्ज न करें।","import_confidence":"विश्वास के साथ इम्पोर्ट करें","import_privacy":"स्टेटमेंट अपलोड करने से SIGORA को आपके बैंक खाते का एक्सेस नहीं मिलता। SIGORA केवल आपके द्वारा दिए गए स्टेटमेंट को प्रोसेस करता है।","source_account":"खाता / स्रोत","import_review_note":"सेव करने से पहले SIGORA की व्याख्या जांचें। अनिश्चित जानकारी चुपचाप गढ़ी नहीं जाती।","account":"खाता","unassigned":"लिंक नहीं","transfer_detected":"ट्रांसफर जैसा मूवमेंट","transaction_source":"स्रोत","cash_account":"भौतिक नकद","wallet_only_after_add":"वॉलेट यहां जोड़ने के बाद ही लेन-देन में दिखाई देगा।"}}

_MONEY_MODEL_I18N["en"].update({"net_worth_incomplete":"Add a current cash/bank balance to calculate net worth accurately.","choose_import_account":"Choose the account this statement belongs to before importing.","review_status":"Review status","looks_good":"Looks good","credit_card_payment":"Credit-card payment — treated as money movement, not a second expense","cash_withdrawal":"Cash withdrawal — treated as movement to physical cash, not spending","self_transfer":"Likely transfer between your own accounts","statement_belongs":"Statement belongs to"})
_MONEY_MODEL_I18N["ta"].update({"net_worth_incomplete":"நிகர சொத்து மதிப்பை துல்லியமாக கணக்கிட தற்போதைய பணம்/வங்கி இருப்பைச் சேர்க்கவும்.","choose_import_account":"இறக்குமதி செய்வதற்கு முன் இந்த அறிக்கை எந்த கணக்கைச் சேர்ந்தது என்பதைத் தேர்வு செய்யவும்.","review_status":"சரிபார்ப்பு நிலை","looks_good":"சரியாக உள்ளது","credit_card_payment":"கிரெடிட் கார்டு கட்டணம் — இரண்டாவது செலவாக அல்ல, பண இயக்கமாக கருதப்பட்டது","cash_withdrawal":"பணம் எடுத்தல் — செலவாக அல்ல, கையிருப்பு பணத்திற்கு மாற்றமாக கருதப்பட்டது","self_transfer":"உங்கள் சொந்த கணக்குகளுக்கிடையிலான பரிமாற்றமாக இருக்கலாம்","statement_belongs":"அறிக்கை சேர்ந்த கணக்கு"})
_MONEY_MODEL_I18N["hi"].update({"net_worth_incomplete":"नेट वर्थ सही गणना करने के लिए मौजूदा कैश/बैंक बैलेंस जोड़ें।","choose_import_account":"इम्पोर्ट करने से पहले वह खाता चुनें जिसका यह स्टेटमेंट है।","review_status":"रिव्यू स्थिति","looks_good":"ठीक दिख रहा है","credit_card_payment":"क्रेडिट-कार्ड भुगतान — दूसरी बार खर्च नहीं, पैसे की आवाजाही माना गया","cash_withdrawal":"नकद निकासी — खर्च नहीं, भौतिक नकद में ट्रांसफर मानी गई","self_transfer":"संभवतः आपके अपने खातों के बीच ट्रांसफर","statement_belongs":"स्टेटमेंट का खाता"})
for _lang,_items in _MONEY_MODEL_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang,{}).update(_items)
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang,{}).update(_items)

_REFUND_POLICY_I18N = {
    "en": {
        "refund_title":"2-day full refund on your first Premium purchase",
        "refund_short":"Request a full refund within 2 calendar days of your initial SIGORA Premium purchase. After that period, the purchase is not eligible for a voluntary refund, except where required by law.",
        "refund_how":"To request a refund, email support.sigora@gmail.com from the email linked to your SIGORA account and include enough payment or subscription details for us to identify the purchase. Never send passwords, OTPs, PINs or full card/bank credentials.",
        "refund_after":"When an approved refund is issued, SIGORA will also cancel the associated subscription from our end so it cannot renew, and Premium access may end once the refund is confirmed.",
        "cancel_not_refund":"Cancelling Premium does not automatically issue a refund.",
        "cancel_cycle":"A normal cancellation stops the next renewal. Your already-paid Premium access continues until the end of the current billing cycle.",
        "refund_policy":"Refund & cancellation policy",
        "initial_purchase":"Initial purchase only",
        "two_calendar_days":"2 calendar days",
        "contact_support_refund":"Request refund by email",
        "refund_checkout":"2-day full refund on your initial purchase. Normal cancellation stops future renewal and does not automatically refund the current payment."
    },
    "ta": {
        "refund_title":"உங்கள் முதல் Premium வாங்குதலுக்கு 2 நாட்களுக்குள் முழு பணத்திருப்பி",
        "refund_short":"உங்கள் முதல் SIGORA Premium வாங்கிய நேரத்திலிருந்து 2 காலண்டர் நாட்களுக்குள் முழு பணத்திருப்பியை கோரலாம். அதன் பிறகு, சட்டப்படி அவசியமான நிலைகளைத் தவிர, அந்த வாங்குதல் விருப்ப பணத்திருப்பிக்கு தகுதியற்றது.",
        "refund_how":"பணத்திருப்பி கோர, உங்கள் SIGORA கணக்குடன் இணைந்த மின்னஞ்சலில் இருந்து support.sigora@gmail.com-க்கு எழுதுங்கள்; வாங்குதலை அடையாளம் காண தேவையான கட்டணம் அல்லது சந்தா விவரங்களை மட்டும் சேர்க்கவும். கடவுச்சொல், OTP, PIN அல்லது முழு கார்டு/வங்கி தகவலை ஒருபோதும் அனுப்ப வேண்டாம்.",
        "refund_after":"அங்கீகரிக்கப்பட்ட பணத்திருப்பி வழங்கப்பட்டதும், மீண்டும் கட்டணம் வசூலிக்கப்படாதபடி தொடர்புடைய சந்தாவையும் SIGORA எங்கள் பக்கத்தில் ரத்து செய்யும்; பணத்திருப்பி உறுதிசெய்யப்பட்டதும் Premium அணுகல் முடிவடையலாம்.",
        "cancel_not_refund":"Premium சந்தாவை ரத்து செய்வது தானாக பணத்திருப்பி வழங்காது.",
        "cancel_cycle":"சாதாரண ரத்து அடுத்த புதுப்பிப்பை நிறுத்தும். ஏற்கனவே செலுத்திய Premium அணுகல் தற்போதைய பில்லிங் காலம் முடியும் வரை தொடரும்.",
        "refund_policy":"பணத்திருப்பி & சந்தா ரத்து கொள்கை",
        "initial_purchase":"முதல் வாங்குதலுக்கு மட்டும்",
        "two_calendar_days":"2 காலண்டர் நாட்கள்",
        "contact_support_refund":"மின்னஞ்சலில் பணத்திருப்பி கோரவும்",
        "refund_checkout":"முதல் வாங்குதலுக்கு 2 நாட்களுக்குள் முழு பணத்திருப்பி. சாதாரண ரத்து எதிர்கால புதுப்பிப்பை மட்டும் நிறுத்தும்; தற்போதைய கட்டணம் தானாக திருப்பி வழங்கப்படாது."
    },
    "hi": {
        "refund_title":"पहली Premium खरीद पर 2 दिनों के भीतर पूरा रिफंड",
        "refund_short":"अपनी शुरुआती SIGORA Premium खरीद के 2 कैलेंडर दिनों के भीतर पूरा रिफंड मांग सकते हैं। इसके बाद, कानून द्वारा आवश्यक मामलों को छोड़कर, वह खरीद स्वैच्छिक रिफंड के लिए पात्र नहीं होगी।",
        "refund_how":"रिफंड के लिए अपने SIGORA खाते से जुड़े ईमेल से support.sigora@gmail.com पर लिखें और खरीद पहचानने के लिए जरूरी भुगतान या सब्सक्रिप्शन विवरण दें। पासवर्ड, OTP, PIN या पूरे कार्ड/बैंक क्रेडेंशियल कभी न भेजें।",
        "refund_after":"स्वीकृत रिफंड जारी होने पर SIGORA संबंधित सब्सक्रिप्शन को हमारी ओर से भी रद्द करेगा ताकि वह दोबारा रिन्यू न हो; रिफंड की पुष्टि होने पर Premium एक्सेस समाप्त हो सकता है।",
        "cancel_not_refund":"Premium सब्सक्रिप्शन रद्द करने से अपने-आप रिफंड नहीं मिलता।",
        "cancel_cycle":"सामान्य कैंसलेशन अगला रिन्यूअल रोकता है। पहले से भुगतान किया गया Premium एक्सेस मौजूदा बिलिंग साइकल के अंत तक जारी रहता है।",
        "refund_policy":"रिफंड और कैंसलेशन नीति",
        "initial_purchase":"केवल पहली खरीद",
        "two_calendar_days":"2 कैलेंडर दिन",
        "contact_support_refund":"ईमेल से रिफंड मांगें",
        "refund_checkout":"पहली खरीद पर 2 दिनों के भीतर पूरा रिफंड। सामान्य कैंसलेशन भविष्य का रिन्यूअल रोकता है और मौजूदा भुगतान को अपने-आप रिफंड नहीं करता।"
    }
}
for _lang, _items in _REFUND_POLICY_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {}).update(_items)

_LEGAL_PAGES_I18N = {
'en': {'legal': 'LEGAL', 'important': 'IMPORTANT', 'last_updated': 'Last updated: 3 September 2026', 'privacy_policy': 'Privacy Policy', 'privacy_intro': 'SIGORA is a personal-finance software platform. This policy explains how we handle information when you create an account and use SIGORA.', 'info_collect': 'Information we collect', 'info_collect_body': 'Depending on the features you use, SIGORA may process your account details, settings, transactions, budgets, goals, imported statements, investment-tracking information, support messages, and technical usage information. If you connect supported financial-data services in the future, data made available through your authorised consent may also be processed.', 'how_use': 'How we use information', 'how_use_body': 'We use information to provide and secure your account, calculate budgets and reports, generate financial insights, prevent duplicate imports, improve product reliability, respond to support requests, and operate optional features you choose to use.', 'ai_features_legal': 'AI features', 'ai_features_body': 'When you use AI Insights, relevant financial context may be sent to our configured AI service provider to generate the requested explanation. SIGORA is designed to minimise the information sent to what is needed for the feature. Do not enter passwords, OTPs, card PINs, or other authentication secrets into AI prompts or support messages.', 'analytics_providers': 'Analytics and service providers', 'analytics_body': 'We may use service providers for cloud hosting, databases, analytics, email, AI processing, market-data retrieval, and payments. These providers process information as needed to deliver their services. Google Analytics may collect usage and device information according to Google’s own terms and controls.', 'security_retention': 'Security and retention', 'security_body': 'We use reasonable technical and organisational safeguards, but no online service can guarantee absolute security. We retain information for as long as needed to provide the service, meet legitimate operational needs, resolve disputes, and comply with applicable legal obligations.', 'your_choices': 'Your choices', 'choices_body': 'You can update certain account information in Settings and may delete your SIGORA account using the account-deletion control. You may also contact us to ask questions about your data or request assistance with access, correction, or deletion, subject to applicable legal retention requirements.', 'contact': 'Contact', 'privacy_contact': 'For privacy questions, contact', 'fin_disclaimer_title': 'Financial & Investment Disclaimer', 'fin_disclaimer_intro': 'SIGORA is a personal-finance software and educational analytics platform. It is not a registered investment adviser, broker, lender, bank, tax adviser, or legal adviser.', 'education_only': 'Educational information only', 'education_body': 'Asset-class examples, risk explanations, allocation illustrations, projections, AI-generated explanations, market charts, and financial-health observations are provided for education and general information. They are not personalised recommendations to buy, sell, hold, or allocate money to any named security or financial product.', 'market_projection': 'Market data and projections', 'market_projection_body': 'Prices, percentage changes, historical charts, and third-party market information may be delayed, incomplete, or temporarily unavailable. Projection tools use assumptions selected by the user and are mathematical illustrations, not forecasts, guarantees, or promised returns.', 'investment_risk': 'Investment risk', 'investment_risk_body': 'Investments can rise or fall in value and you may lose money. Past performance does not guarantee future results. Risk, tax treatment, fees, liquidity, and suitability vary by person and product.', 'your_decisions': 'Your decisions', 'decisions_body': 'You are responsible for evaluating information and making your own financial decisions. For advice tailored to your circumstances, consider an appropriately qualified or regulated professional.', 'support_eyebrow': 'SUPPORT', 'support_title': 'We’re here to help.', 'support_intro': 'If something looks wrong, you find a bug, or you have a question about SIGORA, contact us.', 'email_label': 'EMAIL', 'support_safe': 'For account-specific help, email us from the address associated with your SIGORA account when possible. Never send passwords, OTPs, card PINs, API keys, or full banking credentials.', 'account_data_requests': 'Account and data requests', 'account_data_body': 'You can manage many settings directly inside SIGORA. Account deletion is available in Settings. If you cannot access your account or need help with a data request, email support.', 'payments': 'Payments', 'payments_body': 'SIGORA Premium uses Razorpay for recurring subscription payments. You are charged only after you deliberately complete Razorpay checkout.', 'terms_title': 'Terms of Service', 'terms_intro': 'These Terms govern your use of SIGORA. By using the service, you agree to use it lawfully and responsibly.', 'public_beta': 'Public Beta', 'public_beta_body': 'SIGORA is currently a public-beta product. Features, limits, integrations, pricing, and availability may change as the service develops. We may modify, suspend, or discontinue beta features when reasonably necessary.', 'your_account': 'Your account', 'your_account_body': 'You are responsible for keeping your login credentials secure and for activity performed through your account. Provide accurate information and do not attempt to access another person’s account or bypass service safeguards.', 'your_fin_info': 'Your financial information', 'your_fin_info_body': 'You control the information you add or import into SIGORA. You should review imported transactions, balances, calculations, market information, and generated insights before relying on them. SIGORA may contain errors, delays, or incomplete data.', 'acceptable_use': 'Acceptable use', 'acceptable_use_body': 'Do not misuse SIGORA, interfere with the service, probe or exploit security vulnerabilities, automate abusive traffic, upload malicious content, or use the platform for unlawful activity.', 'premium_payments': 'Premium and payments', 'premium_payments_body': 'SIGORA may offer paid Premium subscriptions through a third-party payment processor such as Razorpay. The price and billing cycle shown at checkout apply to your purchase. Subscriptions renew according to the selected billing cycle until cancelled or otherwise ended. Payment processing, mandates, refunds and settlement may involve the payment provider.', 'rights_body': 'Nothing in these Terms limits any refund, chargeback, cancellation, or consumer rights that cannot lawfully be limited.', 'no_warranties': 'No warranties', 'no_warranties_body': 'SIGORA is provided on an “as available” basis during beta. To the extent permitted by law, we do not guarantee uninterrupted availability, error-free calculations, investment outcomes, or that third-party integrations will always remain available.', 'limitation': 'Limitation and responsibility', 'limitation_body': 'You remain responsible for financial decisions made using information available through SIGORA. Nothing in these Terms excludes rights or liabilities that cannot lawfully be excluded.', 'terms_contact': 'Questions about these Terms can be sent to'},
'ta': {'legal': 'சட்டம்', 'important': 'முக்கியம்', 'last_updated': 'கடைசியாக புதுப்பிக்கப்பட்டது: 3 செப்டம்பர் 2026', 'privacy_policy': 'தனியுரிமைக் கொள்கை', 'privacy_intro': 'SIGORA ஒரு தனிநபர் நிதி மென்பொருள் தளம். நீங்கள் கணக்கை உருவாக்கி SIGORA-வை பயன்படுத்தும் போது தகவலை எவ்வாறு கையாளுகிறோம் என்பதை இந்தக் கொள்கை விளக்குகிறது.', 'info_collect': 'நாங்கள் செயலாக்கும் தகவல்கள்', 'info_collect_body': 'நீங்கள் பயன்படுத்தும் அம்சங்களைப் பொறுத்து, உங்கள் கணக்கு விவரங்கள், அமைப்புகள், பரிவர்த்தனைகள், பட்ஜெட்டுகள், இலக்குகள், இறக்குமதி செய்த அறிக்கைகள், முதலீட்டு கண்காணிப்பு தகவல்கள், உதவி செய்திகள் மற்றும் தொழில்நுட்ப பயன்பாட்டு தகவல்களை SIGORA செயலாக்கலாம். எதிர்காலத்தில் ஆதரிக்கப்படும் நிதித் தரவு சேவைகளை நீங்கள் இணைத்தால், உங்கள் அங்கீகரிக்கப்பட்ட சம்மதத்தின் மூலம் கிடைக்கும் தரவும் செயலாக்கப்படலாம்.', 'how_use': 'தகவலை எவ்வாறு பயன்படுத்துகிறோம்', 'how_use_body': 'உங்கள் கணக்கை வழங்கவும் பாதுகாக்கவும், பட்ஜெட்டுகள் மற்றும் அறிக்கைகளை கணக்கிடவும், நிதி நுண்ணறிவுகளை உருவாக்கவும், நகல் இறக்குமதிகளைத் தடுக்கவும், தயாரிப்பு நம்பகத்தன்மையை மேம்படுத்தவும், உதவி கோரிக்கைகளுக்கு பதிலளிக்கவும், நீங்கள் தேர்வு செய்யும் விருப்ப அம்சங்களை இயக்கவும் தகவலை பயன்படுத்துகிறோம்.', 'ai_features_legal': 'AI அம்சங்கள்', 'ai_features_body': 'AI Insights-ஐ பயன்படுத்தும் போது, கோரிய விளக்கத்தை உருவாக்க தேவையான தொடர்புடைய நிதிச் சூழல் எங்கள் அமைக்கப்பட்ட AI சேவை வழங்குநருக்கு அனுப்பப்படலாம். அம்சத்திற்கு தேவையான அளவுக்கு மட்டுமே தகவலை அனுப்ப SIGORA வடிவமைக்கப்பட்டுள்ளது. AI கேள்விகள் அல்லது உதவி செய்திகளில் கடவுச்சொற்கள், OTP, கார்டு PIN அல்லது பிற அங்கீகார ரகசியங்களை உள்ளிட வேண்டாம்.', 'analytics_providers': 'பகுப்பாய்வு மற்றும் சேவை வழங்குநர்கள்', 'analytics_body': 'கிளவுட் ஹோஸ்டிங், தரவுத்தளங்கள், பகுப்பாய்வு, மின்னஞ்சல், AI செயலாக்கம், சந்தைத் தரவு மற்றும் கட்டணங்களுக்கு சேவை வழங்குநர்களைப் பயன்படுத்தலாம். அவர்கள் தங்கள் சேவைகளை வழங்க தேவையான அளவில் தகவலை செயலாக்குகிறார்கள். Google Analytics, Google-ன் சொந்த விதிமுறைகள் மற்றும் கட்டுப்பாடுகளின்படி பயன்பாடு மற்றும் சாதன தகவலை சேகரிக்கலாம்.', 'security_retention': 'பாதுகாப்பு மற்றும் தரவு வைத்திருப்பு', 'security_body': 'நியாயமான தொழில்நுட்ப மற்றும் அமைப்பு பாதுகாப்புகளைப் பயன்படுத்துகிறோம்; ஆனால் எந்த இணைய சேவையும் முழுமையான பாதுகாப்பை உறுதி செய்ய முடியாது. சேவையை வழங்க, சட்டபூர்வ செயல்பாட்டு தேவைகளை நிறைவேற்ற, பிரச்சினைகளைத் தீர்க்க மற்றும் பொருந்தும் சட்டக் கடமைகளைப் பின்பற்ற தேவையான காலத்திற்கு தகவலை வைத்திருக்கிறோம்.', 'your_choices': 'உங்கள் தேர்வுகள்', 'choices_body': 'Settings-ல் சில கணக்கு தகவல்களை புதுப்பிக்கலாம்; கணக்கு நீக்க கட்டுப்பாட்டைப் பயன்படுத்தி உங்கள் SIGORA கணக்கை நீக்கலாம். பொருந்தும் சட்டபூர்வ தரவு வைத்திருப்பு தேவைகளுக்கு உட்பட்டு, தரவு அணுகல், திருத்தம் அல்லது நீக்கம் தொடர்பான உதவிக்காகவும் எங்களை தொடர்பு கொள்ளலாம்.', 'contact': 'தொடர்பு', 'privacy_contact': 'தனியுரிமை தொடர்பான கேள்விகளுக்கு தொடர்பு கொள்ளவும்', 'fin_disclaimer_title': 'நிதி & முதலீட்டு மறுப்பு', 'fin_disclaimer_intro': 'SIGORA ஒரு தனிநபர் நிதி மென்பொருள் மற்றும் கல்வி பகுப்பாய்வு தளம். இது பதிவு செய்யப்பட்ட முதலீட்டு ஆலோசகர், ப்ரோக்கர், கடன் வழங்குநர், வங்கி, வரி ஆலோசகர் அல்லது சட்ட ஆலோசகர் அல்ல.', 'education_only': 'கல்வி தகவல்களுக்கு மட்டும்', 'education_body': 'சொத்து வகை எடுத்துக்காட்டுகள், ஆபத்து விளக்கங்கள், ஒதுக்கீட்டு எடுத்துக்காட்டுகள், கணிப்புகள், AI உருவாக்கிய விளக்கங்கள், சந்தை வரைபடங்கள் மற்றும் நிதி ஆரோக்கியக் குறிப்புகள் கல்வி மற்றும் பொதுத் தகவலுக்காக மட்டுமே வழங்கப்படுகின்றன. எந்த குறிப்பிட்ட பத்திரம் அல்லது நிதி தயாரிப்பையும் வாங்க, விற்க, வைத்திருக்க அல்லது பணம் ஒதுக்க தனிப்பட்ட பரிந்துரைகள் அல்ல.', 'market_projection': 'சந்தைத் தரவு மற்றும் கணிப்புகள்', 'market_projection_body': 'விலைகள், சதவீத மாற்றங்கள், வரலாற்று வரைபடங்கள் மற்றும் மூன்றாம் தரப்பு சந்தைத் தகவல்கள் தாமதமாகவோ, முழுமையற்றதாகவோ அல்லது தற்காலிகமாக கிடைக்காமலோ இருக்கலாம். கணிப்பு கருவிகள் பயனர் தேர்வு செய்த கருதுகோள்களைப் பயன்படுத்தும் கணித விளக்கங்கள் மட்டுமே; அவை முன்னறிவிப்புகள், உத்தரவாதங்கள் அல்லது உறுதியளிக்கப்பட்ட வருமானங்கள் அல்ல.', 'investment_risk': 'முதலீட்டு ஆபத்து', 'investment_risk_body': 'முதலீடுகளின் மதிப்பு உயரவோ குறையவோலாம்; நீங்கள் பணத்தை இழக்கலாம். கடந்த செயல்திறன் எதிர்கால முடிவுகளை உறுதி செய்யாது. ஆபத்து, வரி, கட்டணங்கள், பணமாக்கும் திறன் மற்றும் பொருத்தம் நபர் மற்றும் தயாரிப்பைப் பொறுத்து மாறும்.', 'your_decisions': 'உங்கள் முடிவுகள்', 'decisions_body': 'தகவலை மதிப்பீடு செய்து உங்கள் நிதி முடிவுகளை நீங்களே எடுப்பது உங்கள் பொறுப்பு. உங்கள் சூழ்நிலைக்கு ஏற்ற ஆலோசனைக்கு தகுதியான அல்லது ஒழுங்குபடுத்தப்பட்ட நிபுணரை அணுகலாம்.', 'support_eyebrow': 'உதவி', 'support_title': 'உங்களுக்கு உதவ நாங்கள் இருக்கிறோம்.', 'support_intro': 'ஏதேனும் தவறாகத் தோன்றினால், பிழை கிடைத்தால் அல்லது SIGORA குறித்து கேள்வி இருந்தால் எங்களை தொடர்பு கொள்ளுங்கள்.', 'email_label': 'மின்னஞ்சல்', 'support_safe': 'கணக்கு சார்ந்த உதவிக்கு, இயன்றால் உங்கள் SIGORA கணக்குடன் இணைந்த மின்னஞ்சலில் இருந்து எழுதுங்கள். கடவுச்சொற்கள், OTP, கார்டு PIN, API keys அல்லது முழு வங்கி உள்நுழைவு தகவலை ஒருபோதும் அனுப்ப வேண்டாம்.', 'account_data_requests': 'கணக்கு மற்றும் தரவு கோரிக்கைகள்', 'account_data_body': 'பல அமைப்புகளை SIGORA-விலேயே நிர்வகிக்கலாம். Settings-ல் கணக்கு நீக்கம் கிடைக்கிறது. கணக்கை அணுக முடியாவிட்டால் அல்லது தரவு கோரிக்கைக்கு உதவி தேவைப்பட்டால் மின்னஞ்சலில் உதவியை தொடர்பு கொள்ளுங்கள்.', 'payments': 'கட்டணங்கள்', 'payments_body': 'SIGORA Premium தொடர்ச்சியான சந்தா கட்டணங்களுக்கு Razorpay-ஐ பயன்படுத்துகிறது. Razorpay checkout-ஐ நீங்கள் தெளிவாக முடித்த பிறகே கட்டணம் வசூலிக்கப்படும்.', 'terms_title': 'சேவை விதிமுறைகள்', 'terms_intro': 'இந்த விதிமுறைகள் SIGORA பயன்பாட்டை நிர்வகிக்கின்றன. சேவையை பயன்படுத்துவதன் மூலம் அதை சட்டபூர்வமாகவும் பொறுப்புடனும் பயன்படுத்த ஒப்புக்கொள்கிறீர்கள்.', 'public_beta': 'பொது பீட்டா', 'public_beta_body': 'SIGORA தற்போது public-beta தயாரிப்பு. சேவை வளரும்போது அம்சங்கள், வரம்புகள், இணைப்புகள், விலை மற்றும் கிடைப்புத் தன்மை மாறலாம். நியாயமான தேவையின்போது beta அம்சங்களை மாற்ற, இடைநிறுத்த அல்லது நிறுத்தலாம்.', 'your_account': 'உங்கள் கணக்கு', 'your_account_body': 'உங்கள் உள்நுழைவு தகவலை பாதுகாப்பாக வைத்திருப்பதும் உங்கள் கணக்கின் மூலம் நடைபெறும் செயல்பாடுகளுக்கும் நீங்கள் பொறுப்பு. சரியான தகவலை வழங்குங்கள்; மற்றொருவரின் கணக்கை அணுகவோ சேவை பாதுகாப்புகளை மீறவோ முயற்சிக்க வேண்டாம்.', 'your_fin_info': 'உங்கள் நிதித் தகவல்', 'your_fin_info_body': 'SIGORA-வில் நீங்கள் சேர்க்கும் அல்லது இறக்குமதி செய்யும் தகவலை நீங்கள் கட்டுப்படுத்துகிறீர்கள். இறக்குமதி செய்யப்பட்ட பரிவர்த்தனைகள், இருப்புகள், கணக்கீடுகள், சந்தைத் தகவல்கள் மற்றும் உருவாக்கப்பட்ட நுண்ணறிவுகளை நம்புவதற்கு முன் சரிபார்க்க வேண்டும். SIGORA-வில் பிழைகள், தாமதங்கள் அல்லது முழுமையற்ற தரவு இருக்கலாம்.', 'acceptable_use': 'ஏற்றுக்கொள்ளத்தக்க பயன்பாடு', 'acceptable_use_body': 'SIGORA-வை தவறாக பயன்படுத்தாதீர்கள்; சேவையில் குறுக்கிடாதீர்கள்; பாதுகாப்பு பலவீனங்களை சோதிக்கவோ பயன்படுத்தவோ வேண்டாம்; தவறான தானியங்கி traffic, தீங்கிழைக்கும் உள்ளடக்கம் அல்லது சட்டவிரோத செயல்களுக்கு தளத்தை பயன்படுத்த வேண்டாம்.', 'premium_payments': 'Premium மற்றும் கட்டணங்கள்', 'premium_payments_body': 'Razorpay போன்ற மூன்றாம் தரப்பு கட்டண செயலி மூலம் SIGORA கட்டண Premium சந்தாக்களை வழங்கலாம். Checkout-ல் காட்டப்படும் விலை மற்றும் billing cycle உங்கள் வாங்குதலுக்கு பொருந்தும். ரத்து செய்யப்படும் வரை அல்லது வேறு விதமாக முடிவடையும் வரை தேர்ந்தெடுத்த billing cycle-க்கு ஏற்ப சந்தா புதுப்பிக்கப்படும். கட்டண செயலாக்கம், mandates, refunds மற்றும் settlement-ல் கட்டண வழங்குநர் ஈடுபடலாம்.', 'rights_body': 'சட்டப்படி கட்டுப்படுத்த முடியாத எந்த பணத்திருப்பி, chargeback, ரத்து அல்லது நுகர்வோர் உரிமைகளையும் இந்த விதிமுறைகள் கட்டுப்படுத்தாது.', 'no_warranties': 'உத்தரவாதங்கள் இல்லை', 'no_warranties_body': 'Beta காலத்தில் SIGORA “கிடைக்கும் நிலையில்” வழங்கப்படுகிறது. சட்டம் அனுமதிக்கும் வரையில், இடையறாத கிடைப்புத் தன்மை, பிழையற்ற கணக்கீடுகள், முதலீட்டு முடிவுகள் அல்லது மூன்றாம் தரப்பு இணைப்புகள் எப்போதும் கிடைக்கும் என்று நாங்கள் உத்தரவாதம் அளிக்கவில்லை.', 'limitation': 'வரம்புகள் மற்றும் பொறுப்பு', 'limitation_body': 'SIGORA மூலம் கிடைக்கும் தகவலை பயன்படுத்தி எடுக்கப்படும் நிதி முடிவுகளுக்கு நீங்கள் பொறுப்பாக இருப்பீர்கள். சட்டப்படி விலக்க முடியாத உரிமைகள் அல்லது பொறுப்புகளை இந்த விதிமுறைகள் விலக்காது.', 'terms_contact': 'இந்த விதிமுறைகள் குறித்த கேள்விகளை அனுப்பலாம்'},
'hi': {'legal': 'कानूनी', 'important': 'महत्वपूर्ण', 'last_updated': 'अंतिम अपडेट: 3 सितंबर 2026', 'privacy_policy': 'प्राइवेसी पॉलिसी', 'privacy_intro': 'SIGORA एक पर्सनल-फाइनेंस सॉफ्टवेयर प्लेटफ़ॉर्म है। यह नीति बताती है कि खाता बनाते और SIGORA का उपयोग करते समय हम जानकारी को कैसे संभालते हैं।', 'info_collect': 'हम कौन-सी जानकारी प्रोसेस करते हैं', 'info_collect_body': 'आपके उपयोग किए गए फीचर्स के आधार पर SIGORA आपके खाते की जानकारी, सेटिंग्स, लेन-देन, बजट, लक्ष्य, इम्पोर्ट किए गए स्टेटमेंट, निवेश-ट्रैकिंग जानकारी, सहायता संदेश और तकनीकी उपयोग जानकारी प्रोसेस कर सकता है। भविष्य में समर्थित वित्तीय-डेटा सेवाएं जोड़ने पर, आपकी अधिकृत सहमति से उपलब्ध डेटा भी प्रोसेस किया जा सकता है।', 'how_use': 'हम जानकारी का उपयोग कैसे करते हैं', 'how_use_body': 'हम जानकारी का उपयोग आपका खाता उपलब्ध कराने और सुरक्षित रखने, बजट और रिपोर्ट की गणना, वित्तीय इनसाइट बनाने, डुप्लिकेट इम्पोर्ट रोकने, उत्पाद की विश्वसनीयता सुधारने, सहायता अनुरोधों का जवाब देने और आपके चुने वैकल्पिक फीचर्स चलाने के लिए करते हैं।', 'ai_features_legal': 'AI फीचर्स', 'ai_features_body': 'AI Insights का उपयोग करते समय, मांगी गई व्याख्या बनाने के लिए जरूरी वित्तीय संदर्भ हमारे कॉन्फ़िगर किए गए AI सेवा प्रदाता को भेजा जा सकता है। SIGORA को फीचर के लिए जरूरी जानकारी तक ही डेटा सीमित रखने के लिए डिज़ाइन किया गया है। AI प्रॉम्प्ट या सहायता संदेश में पासवर्ड, OTP, कार्ड PIN या अन्य प्रमाणीकरण रहस्य न डालें।', 'analytics_providers': 'एनालिटिक्स और सेवा प्रदाता', 'analytics_body': 'हम क्लाउड होस्टिंग, डेटाबेस, एनालिटिक्स, ईमेल, AI प्रोसेसिंग, मार्केट डेटा और भुगतान के लिए सेवा प्रदाताओं का उपयोग कर सकते हैं। वे अपनी सेवाएं देने के लिए आवश्यक जानकारी प्रोसेस करते हैं। Google Analytics, Google की अपनी शर्तों और नियंत्रणों के अनुसार उपयोग और डिवाइस जानकारी एकत्र कर सकता है।', 'security_retention': 'सुरक्षा और डेटा रिटेंशन', 'security_body': 'हम उचित तकनीकी और संगठनात्मक सुरक्षा उपाय अपनाते हैं, लेकिन कोई भी ऑनलाइन सेवा पूर्ण सुरक्षा की गारंटी नहीं दे सकती। सेवा देने, वैध संचालन जरूरतें पूरी करने, विवाद सुलझाने और लागू कानूनी दायित्वों का पालन करने के लिए आवश्यक अवधि तक जानकारी रखी जाती है।', 'your_choices': 'आपके विकल्प', 'choices_body': 'आप Settings में कुछ खाता जानकारी अपडेट कर सकते हैं और account-deletion control से अपना SIGORA खाता हटा सकते हैं। लागू कानूनी डेटा-रिटेंशन आवश्यकताओं के अधीन, डेटा एक्सेस, सुधार या हटाने में सहायता के लिए भी हमसे संपर्क कर सकते हैं।', 'contact': 'संपर्क', 'privacy_contact': 'प्राइवेसी से जुड़े सवालों के लिए संपर्क करें', 'fin_disclaimer_title': 'वित्तीय और निवेश अस्वीकरण', 'fin_disclaimer_intro': 'SIGORA एक पर्सनल-फाइनेंस सॉफ्टवेयर और शैक्षिक एनालिटिक्स प्लेटफ़ॉर्म है। यह पंजीकृत निवेश सलाहकार, ब्रोकर, ऋणदाता, बैंक, टैक्स सलाहकार या कानूनी सलाहकार नहीं है।', 'education_only': 'केवल शैक्षिक जानकारी', 'education_body': 'एसेट-क्लास उदाहरण, जोखिम व्याख्याएं, आवंटन उदाहरण, प्रोजेक्शन, AI द्वारा बनाई गई व्याख्याएं, मार्केट चार्ट और वित्तीय-स्वास्थ्य संकेत केवल शिक्षा और सामान्य जानकारी के लिए हैं। ये किसी नामित सिक्योरिटी या वित्तीय उत्पाद को खरीदने, बेचने, रखने या उसमें पैसा लगाने की व्यक्तिगत सलाह नहीं हैं।', 'market_projection': 'मार्केट डेटा और प्रोजेक्शन', 'market_projection_body': 'कीमतें, प्रतिशत बदलाव, ऐतिहासिक चार्ट और थर्ड-पार्टी मार्केट जानकारी देर से, अधूरी या अस्थायी रूप से अनुपलब्ध हो सकती है। प्रोजेक्शन टूल उपयोगकर्ता द्वारा चुनी गई मान्यताओं पर आधारित गणितीय उदाहरण हैं; वे पूर्वानुमान, गारंटी या वादा किए गए रिटर्न नहीं हैं।', 'investment_risk': 'निवेश जोखिम', 'investment_risk_body': 'निवेश का मूल्य बढ़ या घट सकता है और आपको नुकसान हो सकता है। पिछला प्रदर्शन भविष्य के परिणामों की गारंटी नहीं देता। जोखिम, टैक्स, फीस, लिक्विडिटी और उपयुक्तता व्यक्ति और उत्पाद के अनुसार बदलती है।', 'your_decisions': 'आपके निर्णय', 'decisions_body': 'जानकारी का मूल्यांकन करना और अपने वित्तीय निर्णय लेना आपकी जिम्मेदारी है। अपनी परिस्थितियों के अनुसार सलाह के लिए उचित रूप से योग्य या विनियमित पेशेवर से संपर्क करने पर विचार करें।', 'support_eyebrow': 'सहायता', 'support_title': 'हम आपकी मदद के लिए यहां हैं।', 'support_intro': 'अगर कुछ गलत लगे, कोई बग मिले या SIGORA के बारे में सवाल हो, तो हमसे संपर्क करें।', 'email_label': 'ईमेल', 'support_safe': 'खाता-विशिष्ट सहायता के लिए, संभव हो तो अपने SIGORA खाते से जुड़े ईमेल से लिखें। पासवर्ड, OTP, कार्ड PIN, API keys या पूरे बैंकिंग क्रेडेंशियल कभी न भेजें।', 'account_data_requests': 'खाता और डेटा अनुरोध', 'account_data_body': 'कई सेटिंग्स सीधे SIGORA में प्रबंधित की जा सकती हैं। Settings में खाता हटाने का विकल्प उपलब्ध है। अगर आप खाते तक नहीं पहुंच पा रहे हैं या डेटा अनुरोध में मदद चाहिए, तो सहायता को ईमेल करें।', 'payments': 'भुगतान', 'payments_body': 'SIGORA Premium आवर्ती सब्सक्रिप्शन भुगतान के लिए Razorpay का उपयोग करता है। Razorpay checkout को जानबूझकर पूरा करने के बाद ही आपसे शुल्क लिया जाता है।', 'terms_title': 'सेवा की शर्तें', 'terms_intro': 'ये शर्तें SIGORA के आपके उपयोग को नियंत्रित करती हैं। सेवा का उपयोग करके आप इसे कानूनी और जिम्मेदार तरीके से उपयोग करने के लिए सहमत होते हैं।', 'public_beta': 'पब्लिक बीटा', 'public_beta_body': 'SIGORA अभी public-beta उत्पाद है। सेवा के विकसित होने के साथ फीचर्स, सीमाएं, इंटीग्रेशन, कीमत और उपलब्धता बदल सकती है। उचित आवश्यकता होने पर हम beta फीचर्स को बदल, रोक या बंद कर सकते हैं।', 'your_account': 'आपका खाता', 'your_account_body': 'अपने लॉगिन क्रेडेंशियल सुरक्षित रखना और अपने खाते से होने वाली गतिविधि की जिम्मेदारी आपकी है। सही जानकारी दें और किसी अन्य व्यक्ति के खाते तक पहुंचने या सेवा सुरक्षा को बायपास करने की कोशिश न करें।', 'your_fin_info': 'आपकी वित्तीय जानकारी', 'your_fin_info_body': 'SIGORA में जो जानकारी आप जोड़ते या इम्पोर्ट करते हैं, उस पर आपका नियंत्रण है। इम्पोर्ट किए गए लेन-देन, बैलेंस, गणनाएं, मार्केट जानकारी और बनाई गई इनसाइट पर भरोसा करने से पहले उनकी समीक्षा करें। SIGORA में त्रुटियां, देरी या अधूरा डेटा हो सकता है।', 'acceptable_use': 'स्वीकार्य उपयोग', 'acceptable_use_body': 'SIGORA का दुरुपयोग न करें, सेवा में बाधा न डालें, सुरक्षा कमजोरियों को जांचने या उनका फायदा उठाने की कोशिश न करें, दुरुपयोग वाला ऑटोमेटेड ट्रैफिक या हानिकारक सामग्री न भेजें और प्लेटफ़ॉर्म का गैरकानूनी गतिविधि के लिए उपयोग न करें।', 'premium_payments': 'Premium और भुगतान', 'premium_payments_body': 'SIGORA Razorpay जैसे थर्ड-पार्टी भुगतान प्रोसेसर के माध्यम से भुगतान वाले Premium सब्सक्रिप्शन दे सकता है। Checkout पर दिखाई गई कीमत और billing cycle आपकी खरीद पर लागू होती है। रद्द या अन्यथा समाप्त होने तक चुने गए billing cycle के अनुसार सब्सक्रिप्शन रिन्यू होता है। भुगतान प्रोसेसिंग, mandates, refunds और settlement में भुगतान प्रदाता शामिल हो सकता है।', 'rights_body': 'इन शर्तों में ऐसा कुछ भी नहीं है जो कानूनन सीमित न किए जा सकने वाले refund, chargeback, cancellation या consumer rights को सीमित करे।', 'no_warranties': 'कोई वारंटी नहीं', 'no_warranties_body': 'Beta के दौरान SIGORA “जैसा उपलब्ध है” आधार पर दिया जाता है। कानून द्वारा अनुमत सीमा तक हम बिना रुकावट उपलब्धता, त्रुटिरहित गणनाओं, निवेश परिणामों या थर्ड-पार्टी इंटीग्रेशन के हमेशा उपलब्ध रहने की गारंटी नहीं देते।', 'limitation': 'सीमा और जिम्मेदारी', 'limitation_body': 'SIGORA के माध्यम से उपलब्ध जानकारी का उपयोग करके लिए गए वित्तीय निर्णयों की जिम्मेदारी आपकी रहती है। ये शर्तें उन अधिकारों या दायित्वों को बाहर नहीं करतीं जिन्हें कानूनन बाहर नहीं किया जा सकता।', 'terms_contact': 'इन शर्तों के बारे में सवाल भेजें'},
}
for _lang, _items in _LEGAL_PAGES_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {}).update(_items)

# What-If V2 visible language coverage. Financial maths is language-independent.
_WHAT_IF_V2_I18N = {
    "ta": {
        "Ask Sigora about a financial decision":"ஒரு நிதி முடிவைப் பற்றி SIGORA-விடம் கேளுங்கள்",
        "Ask naturally — Sigora will work out the financial mechanics.":"இயல்பாகக் கேளுங்கள் — நிதிக் கணக்குகளை SIGORA பார்த்துக்கொள்ளும்.",
        "Will I be able to buy an iPhone?":"நான் ஒரு iPhone வாங்க முடியுமா?",
        "Ask Sigora →":"SIGORA-விடம் கேள் →", "What price are you expecting to pay?":"நீங்கள் எவ்வளவு விலையில் வாங்க திட்டமிட்டுள்ளீர்கள்?",
        "Expected price":"எதிர்பார்க்கும் விலை", "Continue simulation →":"சிமுலேஷனைத் தொடரவும் →",
        "SIGORA VERDICT":"SIGORA முடிவு", "Looks manageable":"சமாளிக்கக்கூடியதாக தெரிகிறது", "Proceed with caution":"கவனமாக முடிவு செய்யுங்கள்",
        "High impact on your buffer":"உங்கள் நிதி இருப்பில் அதிக தாக்கம்", "Not enough data yet":"இன்னும் போதுமான தரவு இல்லை",
        "Recorded buffer now":"தற்போதைய பதிவு செய்யப்பட்ட இருப்பு", "After this decision":"இந்த முடிவுக்குப் பிறகு", "Buffer used":"பயன்படும் இருப்பு",
        "Recent monthly savings pace":"சமீபத்திய மாத சேமிப்பு வேகம்", "Estimated recovery time":"மீட்பு கால மதிப்பீடு", "months":"மாதங்கள்",
        "Goal in view":"கவனத்தில் உள்ள இலக்கு", "Why Sigora says this":"SIGORA ஏன் இதைச் சொல்கிறது",
        "This fits inside your recorded savings buffer.":"இது உங்கள் பதிவு செய்யப்பட்ட சேமிப்பு இருப்புக்குள் வருகிறது.",
        "This would use a large share of your recorded savings buffer.":"இது உங்கள் பதிவு செய்யப்பட்ட சேமிப்பு இருப்பின் பெரிய பகுதியைப் பயன்படுத்தும்.",
        "This is larger than your currently recorded savings buffer.":"இது தற்போது பதிவு செய்யப்பட்ட சேமிப்பு இருப்பை விட அதிகம்.",
        "Add more transaction history before relying on this simulation.":"இந்த சிமுலேஷனை நம்புவதற்கு முன் மேலும் பரிவர்த்தனை வரலாற்றைச் சேர்க்கவும்.",
        "AI interprets your question. Sigora's recorded financial data does the calculation.":"AI உங்கள் கேள்வியைப் புரிந்துகொள்கிறது. கணக்கை SIGORA-வில் பதிவு செய்யப்பட்ட நிதித் தரவு செய்கிறது."
    },
    "hi": {
        "Ask Sigora about a financial decision":"किसी वित्तीय फैसले के बारे में SIGORA से पूछें",
        "Ask naturally — Sigora will work out the financial mechanics.":"स्वाभाविक रूप से पूछें — वित्तीय गणना SIGORA संभालेगा।",
        "Will I be able to buy an iPhone?":"क्या मैं iPhone खरीद पाऊंगा?",
        "Ask Sigora →":"SIGORA से पूछें →", "What price are you expecting to pay?":"आप कितनी कीमत चुकाने की उम्मीद कर रहे हैं?",
        "Expected price":"अपेक्षित कीमत", "Continue simulation →":"सिमुलेशन जारी रखें →",
        "SIGORA VERDICT":"SIGORA निष्कर्ष", "Looks manageable":"संभव लगता है", "Proceed with caution":"सावधानी से आगे बढ़ें",
        "High impact on your buffer":"आपके वित्तीय बफर पर बड़ा असर", "Not enough data yet":"अभी पर्याप्त डेटा नहीं है",
        "Recorded buffer now":"अभी दर्ज बफर", "After this decision":"इस फैसले के बाद", "Buffer used":"बफर का उपयोग",
        "Recent monthly savings pace":"हाल की मासिक बचत गति", "Estimated recovery time":"अनुमानित रिकवरी समय", "months":"महीने",
        "Goal in view":"ध्यान में लक्ष्य", "Why Sigora says this":"SIGORA ऐसा क्यों कहता है",
        "This fits inside your recorded savings buffer.":"यह आपके दर्ज बचत बफर के भीतर है।",
        "This would use a large share of your recorded savings buffer.":"यह आपके दर्ज बचत बफर का बड़ा हिस्सा इस्तेमाल करेगा।",
        "This is larger than your currently recorded savings buffer.":"यह आपके वर्तमान दर्ज बचत बफर से बड़ा है।",
        "Add more transaction history before relying on this simulation.":"इस सिमुलेशन पर भरोसा करने से पहले और लेन-देन इतिहास जोड़ें।",
        "AI interprets your question. Sigora's recorded financial data does the calculation.":"AI आपके सवाल को समझता है। गणना SIGORA में दर्ज वित्तीय डेटा करता है।"
    }
}
for _lang, _items in _WHAT_IF_V2_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {}).update(_items)

# Final dashboard localization pass: these system-generated strings are stored
# in English internally, but must follow the user's active app language.
_DASHBOARD_SYSTEM_I18N = {
    "ta": {
        "Not enough data yet. Add income or expense transactions to unlock your Financial Health Score.": "இன்னும் போதுமான தரவு இல்லை. உங்கள் நிதி ஆரோக்கிய மதிப்பெண்ணைத் திறக்க வருமானம் அல்லது செலவு பரிவர்த்தனைகளைச் சேர்க்கவும்.",
        "Welcome to Sigora": "SIGORA-வுக்கு வரவேற்கிறோம்",
        "Welcome to Sigora 👋": "SIGORA-வுக்கு வரவேற்கிறோம் 👋",
        "You're all set to start tracking your money, setting goals and understanding your finances better. Want to unlock more? Try Sigora Premium for advanced AI insights, forecasting, What-If simulations and more.": "உங்கள் பணத்தை கண்காணிக்கவும், இலக்குகளை அமைக்கவும், உங்கள் நிதியை சிறப்பாகப் புரிந்துகொள்ளவும் நீங்கள் தயாராக உள்ளீர்கள். மேலும் அம்சங்களைத் திறக்க விரும்புகிறீர்களா? மேம்பட்ட AI நுண்ணறிவுகள், முன்கணிப்புகள், What-If சிமுலேஷன்கள் மற்றும் பல அம்சங்களுக்கு SIGORA Premium-ஐ முயற்சிக்கவும்.",
        "You’re all set to start tracking your money, setting goals and understanding your finances better. Want to unlock more? Try Sigora Premium for advanced AI insights, forecasting, What-If simulations and more.": "உங்கள் பணத்தை கண்காணிக்கவும், இலக்குகளை அமைக்கவும், உங்கள் நிதியை சிறப்பாகப் புரிந்துகொள்ளவும் நீங்கள் தயாராக உள்ளீர்கள். மேலும் அம்சங்களைத் திறக்க விரும்புகிறீர்களா? மேம்பட்ட AI நுண்ணறிவுகள், முன்கணிப்புகள், What-If சிமுலேஷன்கள் மற்றும் பல அம்சங்களுக்கு SIGORA Premium-ஐ முயற்சிக்கவும்.",
    },
    "hi": {
        "Not enough data yet. Add income or expense transactions to unlock your Financial Health Score.": "अभी पर्याप्त डेटा नहीं है। अपना वित्तीय स्वास्थ्य स्कोर अनलॉक करने के लिए आय या खर्च के लेन-देन जोड़ें।",
        "Welcome to Sigora": "SIGORA में आपका स्वागत है",
        "Welcome to Sigora 👋": "SIGORA में आपका स्वागत है 👋",
        "You're all set to start tracking your money, setting goals and understanding your finances better. Want to unlock more? Try Sigora Premium for advanced AI insights, forecasting, What-If simulations and more.": "अब आप अपने पैसे को ट्रैक करने, लक्ष्य तय करने और अपनी वित्तीय स्थिति को बेहतर समझने के लिए तैयार हैं। और फीचर्स अनलॉक करना चाहते हैं? उन्नत AI इनसाइट्स, पूर्वानुमान, What-If सिमुलेशन और अधिक के लिए SIGORA Premium आज़माएं।",
        "You’re all set to start tracking your money, setting goals and understanding your finances better. Want to unlock more? Try Sigora Premium for advanced AI insights, forecasting, What-If simulations and more.": "अब आप अपने पैसे को ट्रैक करने, लक्ष्य तय करने और अपनी वित्तीय स्थिति को बेहतर समझने के लिए तैयार हैं। और फीचर्स अनलॉक करना चाहते हैं? उन्नत AI इनसाइट्स, पूर्वानुमान, What-If सिमुलेशन और अधिक के लिए SIGORA Premium आज़माएं।",
    },
}
for _lang, _items in _DASHBOARD_SYSTEM_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {}).update(_items)


def _sigora_language():
    lang = session.get("sigora_language", "en")
    return lang if lang in SIGORA_LANGUAGES else "en"

def _t(key):
    lang = _sigora_language()
    return SIGORA_TRANSLATIONS.get(lang, SIGORA_TRANSLATIONS["en"]).get(key, SIGORA_TRANSLATIONS["en"].get(key, key))

# Keep secrets out of source code. Set SECRET_KEY in the deployment environment.
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

@app.before_request
def _ensure_launch_schema():
    ensure_feature_schema()
    ensure_investment_schema()
    ensure_admin_schema()
    # Admin sessions are intentionally shorter and independent of normal user sessions.
    if session.get("admin_user_id"):
        now = datetime.utcnow()
        last_raw = session.get("admin_last_seen")
        try:
            last_seen = datetime.fromisoformat(last_raw) if last_raw else now
        except Exception:
            last_seen = now
        if now - last_seen > timedelta(minutes=30):
            session.pop("admin_user_id", None)
            session.pop("admin_last_seen", None)
            session.pop("admin_csrf_token", None)
            if request.path.startswith("/admin") and request.path != "/admin/login":
                return redirect("/admin/login?expired=1")
        else:
            session["admin_last_seen"] = now.isoformat()


# Complete Premium lifecycle localization: checkout, activation, usage, cancellation and billing states.
_PREMIUM_LIFECYCLE_I18N = {
"en": {
"Make Sigora think harder.":"Make SIGORA think harder.","Advanced intelligence for people who want more than basic tracking.":"Advanced intelligence for people who want more than basic tracking.","Current Premium price · Secure recurring billing powered by Razorpay.":"Current Premium price · Secure recurring billing powered by Razorpay.","FREE VS PREMIUM":"FREE VS PREMIUM","Everything at a glance.":"Everything at a glance.","ACTIVE":"ACTIVE","Feature":"Feature","Free":"Free","AI-powered analyses":"AI-powered analyses","Advanced AI Insights":"Advanced AI Insights","Goal Intelligence":"Goal Intelligence","Predictive budget-risk engine":"Predictive budget-risk engine","Financial Health Score":"Financial Health Score","What-if purchase simulator":"What-if purchase simulator","Spending & income forecasts":"Spending & income forecasts","Personalized recommendations":"Personalized recommendations","Advanced reports":"Advanced reports","Gamification":"Gamification","Budget & goal tools":"Budget & goal tools","Limited":"Limited","Preview":"Preview","LIVE FINANCIAL SIGNAL":"LIVE FINANCIAL SIGNAL","Financial Health Score unlocks with your data":"Financial Health Score unlocks with your data","Open Intelligence →":"Open Intelligence →","AI USAGE":"AI USAGE","analyses used this month":"analyses used this month","Daily safety limit:":"Daily safety limit:","PLAN":"PLAN","Premium is active.":"Premium is active.","Ready when you are.":"Ready when you are.","Your Premium AI allowance is active.":"Your Premium AI allowance is active.","Upgrade securely with Razorpay. Your Premium access activates after payment confirmation.":"Upgrade securely with Razorpay. Your Premium access activates after payment confirmation.","Cancellation scheduled":"Cancellation scheduled","Cancel at billing-cycle end":"Cancel at billing-cycle end","Coupon code (optional)":"Coupon code (optional)","Upgrade for":"Upgrade for","Checkout coming soon":"Checkout coming soon","That coupon is invalid, expired, or already used.":"That coupon is invalid, expired, or already used.","Live checkout is not configured yet. Add your Razorpay credentials after your merchant account is ready.":"Live checkout is not configured yet. Add your Razorpay credentials after your merchant account is ready.","Razorpay could not start this subscription. No charge was made. Please try again shortly or contact support if it continues.":"Razorpay could not start this subscription. No charge was made. Please try again shortly or contact support if it continues.","We couldn't start checkout. No charge was made. Please try again later.":"We couldn't start checkout. No charge was made. Please try again later.","Payment verified. Premium will unlock automatically after Razorpay confirms the subscription.":"Payment verified. Premium will unlock automatically after Razorpay confirms the subscription.","We could not verify that payment. Premium was not activated.":"We could not verify that payment. Premium was not activated.","We could not cancel the subscription. Please try again.":"We could not cancel the subscription. Please try again.","SECURE CHECKOUT":"SECURE CHECKOUT","Finish your Premium upgrade.":"Finish your Premium upgrade.","You're subscribing to SIGORA Premium at":"You're subscribing to SIGORA Premium at","You'll complete payment securely through Razorpay.":"You'll complete payment securely through Razorpay.","Open secure checkout →":"Open secure checkout →","month":"month","Launch price":"Launch price","Explore Premium →":"Explore Premium →","Premium active":"Premium active","Unlock Premium":"Unlock Premium","analyses this month":"analyses this month"},
"ta": {
"Make Sigora think harder.":"SIGORA-வின் நுண்ணறிவை மேலும் பயன்படுத்துங்கள்.","Advanced intelligence for people who want more than basic tracking.":"அடிப்படை கண்காணிப்பைத் தாண்டி ஆழமான நிதி நுண்ணறிவு விரும்புபவர்களுக்காக.","Current Premium price · Secure recurring billing powered by Razorpay.":"தற்போதைய பிரீமியம் விலை · Razorpay மூலம் பாதுகாப்பான தொடர்ச்சியான கட்டணம்.","FREE VS PREMIUM":"இலவசம் vs பிரீமியம்","Everything at a glance.":"அனைத்தையும் ஒரே பார்வையில்.","ACTIVE":"செயலில்","Feature":"அம்சம்","Free":"இலவசம்","AI-powered analyses":"AI ஆதரவு பகுப்பாய்வுகள்","Advanced AI Insights":"மேம்பட்ட AI நுண்ணறிவுகள்","Goal Intelligence":"இலக்கு நுண்ணறிவு","Predictive budget-risk engine":"பட்ஜெட் அபாய முன்கணிப்பு","Financial Health Score":"நிதி ஆரோக்கிய மதிப்பெண்","What-if purchase simulator":"வாங்கினால் என்ன ஆகும் சிமுலேட்டர்","Spending & income forecasts":"செலவு மற்றும் வருமான முன்கணிப்புகள்","Personalized recommendations":"தனிப்பயன் பரிந்துரைகள்","Advanced reports":"மேம்பட்ட அறிக்கைகள்","Gamification":"விளையாட்டுமயமாக்கல்","Budget & goal tools":"பட்ஜெட் மற்றும் இலக்கு கருவிகள்","Limited":"வரம்புடன்","Preview":"முன்னோட்டம்","LIVE FINANCIAL SIGNAL":"நேரடி நிதி சிக்னல்","Financial Health Score unlocks with your data":"உங்கள் தரவு சேர்க்கப்பட்டதும் நிதி ஆரோக்கிய மதிப்பெண் திறக்கும்","Open Intelligence →":"நிதி நுண்ணறிவைத் திற →","AI USAGE":"AI பயன்பாடு","analyses used this month":"இந்த மாதம் பயன்படுத்திய பகுப்பாய்வுகள்","Daily safety limit:":"தினசரி பாதுகாப்பு வரம்பு:","PLAN":"திட்டம்","Premium is active.":"பிரீமியம் செயலில் உள்ளது.","Ready when you are.":"நீங்கள் தயாரானதும் தொடங்கலாம்.","Your Premium AI allowance is active.":"உங்கள் பிரீமியம் AI பயன்பாட்டு வரம்பு செயலில் உள்ளது.","Upgrade securely with Razorpay. Your Premium access activates after payment confirmation.":"Razorpay மூலம் பாதுகாப்பாக மேம்படுத்துங்கள். கட்டணம் உறுதிப்படுத்தப்பட்டதும் பிரீமியம் அணுகல் செயல்படும்.","Cancellation scheduled":"ரத்து செய்ய திட்டமிடப்பட்டது","Cancel at billing-cycle end":"பில்லிங் சுழற்சி முடிவில் ரத்து செய்","Coupon code (optional)":"கூப்பன் குறியீடு (விருப்பம்)","Upgrade for":"இந்த விலையில் மேம்படுத்து","Checkout coming soon":"செக்அவுட் விரைவில் வருகிறது","That coupon is invalid, expired, or already used.":"அந்த கூப்பன் செல்லாது, காலாவதியானது அல்லது ஏற்கனவே பயன்படுத்தப்பட்டது.","Live checkout is not configured yet. Add your Razorpay credentials after your merchant account is ready.":"நேரடி செக்அவுட் இன்னும் அமைக்கப்படவில்லை. உங்கள் வணிகர் கணக்கு தயாரானதும் Razorpay விவரங்களைச் சேர்க்கவும்.","Razorpay could not start this subscription. No charge was made. Please try again shortly or contact support if it continues.":"Razorpay இந்த சந்தாவை தொடங்க முடியவில்லை. எந்த கட்டணமும் வசூலிக்கப்படவில்லை. மீண்டும் முயற்சிக்கவும்; பிரச்சனை தொடர்ந்தால் உதவியைத் தொடர்புகொள்ளவும்.","We couldn't start checkout. No charge was made. Please try again later.":"செக்அவுட்டை தொடங்க முடியவில்லை. எந்த கட்டணமும் வசூலிக்கப்படவில்லை. பின்னர் மீண்டும் முயற்சிக்கவும்.","Payment verified. Premium will unlock automatically after Razorpay confirms the subscription.":"கட்டணம் சரிபார்க்கப்பட்டது. Razorpay சந்தாவை உறுதிப்படுத்தியதும் பிரீமியம் தானாக செயல்படும்.","We could not verify that payment. Premium was not activated.":"அந்த கட்டணத்தை சரிபார்க்க முடியவில்லை. பிரீமியம் செயல்படுத்தப்படவில்லை.","We could not cancel the subscription. Please try again.":"சந்தாவை ரத்து செய்ய முடியவில்லை. மீண்டும் முயற்சிக்கவும்.","SECURE CHECKOUT":"பாதுகாப்பான செக்அவுட்","Finish your Premium upgrade.":"உங்கள் பிரீமியம் மேம்பாட்டை நிறைவு செய்யுங்கள்.","You're subscribing to SIGORA Premium at":"நீங்கள் SIGORA பிரீமியத்தை இந்த விலையில் சந்தா செய்கிறீர்கள்","You'll complete payment securely through Razorpay.":"Razorpay மூலம் கட்டணத்தை பாதுகாப்பாக நிறைவு செய்வீர்கள்.","Open secure checkout →":"பாதுகாப்பான செக்அவுட்டைத் திற →","month":"மாதம்","Launch price":"அறிமுக விலை","Explore Premium →":"பிரீமியத்தைப் பாருங்கள் →","Premium active":"பிரீமியம் செயலில்","Unlock Premium":"பிரீமியத்தைத் திற","analyses this month":"இந்த மாத பகுப்பாய்வுகள்"},
"hi": {
"Make Sigora think harder.":"SIGORA की इंटेलिजेंस का और अधिक उपयोग करें।","Advanced intelligence for people who want more than basic tracking.":"उन लोगों के लिए उन्नत वित्तीय इंटेलिजेंस जो केवल बेसिक ट्रैकिंग से अधिक चाहते हैं।","Current Premium price · Secure recurring billing powered by Razorpay.":"मौजूदा प्रीमियम कीमत · Razorpay द्वारा सुरक्षित आवर्ती बिलिंग।","FREE VS PREMIUM":"फ्री बनाम प्रीमियम","Everything at a glance.":"सब कुछ एक नज़र में।","ACTIVE":"सक्रिय","Feature":"फीचर","Free":"फ्री","AI-powered analyses":"AI-संचालित विश्लेषण","Advanced AI Insights":"उन्नत AI इनसाइट्स","Goal Intelligence":"लक्ष्य इंटेलिजेंस","Predictive budget-risk engine":"बजट जोखिम पूर्वानुमान इंजन","Financial Health Score":"वित्तीय स्वास्थ्य स्कोर","What-if purchase simulator":"खरीद परिदृश्य सिमुलेटर","Spending & income forecasts":"खर्च और आय के पूर्वानुमान","Personalized recommendations":"व्यक्तिगत सुझाव","Advanced reports":"उन्नत रिपोर्ट","Gamification":"गेमिफिकेशन","Budget & goal tools":"बजट और लक्ष्य टूल्स","Limited":"सीमित","Preview":"प्रीव्यू","LIVE FINANCIAL SIGNAL":"लाइव वित्तीय संकेत","Financial Health Score unlocks with your data":"आपका डेटा जुड़ने पर वित्तीय स्वास्थ्य स्कोर उपलब्ध होगा","Open Intelligence →":"इंटेलिजेंस खोलें →","AI USAGE":"AI उपयोग","analyses used this month":"इस महीने उपयोग किए गए विश्लेषण","Daily safety limit:":"दैनिक सुरक्षा सीमा:","PLAN":"प्लान","Premium is active.":"प्रीमियम सक्रिय है।","Ready when you are.":"जब आप तैयार हों।","Your Premium AI allowance is active.":"आपकी प्रीमियम AI उपयोग सीमा सक्रिय है।","Upgrade securely with Razorpay. Your Premium access activates after payment confirmation.":"Razorpay से सुरक्षित रूप से अपग्रेड करें। भुगतान की पुष्टि के बाद प्रीमियम एक्सेस सक्रिय होगा।","Cancellation scheduled":"रद्दीकरण निर्धारित है","Cancel at billing-cycle end":"बिलिंग चक्र के अंत में रद्द करें","Coupon code (optional)":"कूपन कोड (वैकल्पिक)","Upgrade for":"इस कीमत पर अपग्रेड करें","Checkout coming soon":"चेकआउट जल्द उपलब्ध होगा","That coupon is invalid, expired, or already used.":"यह कूपन अमान्य, समाप्त या पहले ही उपयोग किया जा चुका है।","Live checkout is not configured yet. Add your Razorpay credentials after your merchant account is ready.":"लाइव चेकआउट अभी कॉन्फ़िगर नहीं है। मर्चेंट खाता तैयार होने के बाद Razorpay विवरण जोड़ें।","Razorpay could not start this subscription. No charge was made. Please try again shortly or contact support if it continues.":"Razorpay इस सदस्यता को शुरू नहीं कर सका। कोई शुल्क नहीं लिया गया। थोड़ी देर बाद फिर कोशिश करें; समस्या जारी रहे तो सहायता से संपर्क करें।","We couldn't start checkout. No charge was made. Please try again later.":"हम चेकआउट शुरू नहीं कर सके। कोई शुल्क नहीं लिया गया। बाद में फिर कोशिश करें।","Payment verified. Premium will unlock automatically after Razorpay confirms the subscription.":"भुगतान सत्यापित हो गया। Razorpay द्वारा सदस्यता की पुष्टि के बाद प्रीमियम अपने आप सक्रिय होगा।","We could not verify that payment. Premium was not activated.":"हम उस भुगतान को सत्यापित नहीं कर सके। प्रीमियम सक्रिय नहीं हुआ।","We could not cancel the subscription. Please try again.":"हम सदस्यता रद्द नहीं कर सके। कृपया फिर कोशिश करें।","SECURE CHECKOUT":"सुरक्षित चेकआउट","Finish your Premium upgrade.":"अपना प्रीमियम अपग्रेड पूरा करें।","You're subscribing to SIGORA Premium at":"आप SIGORA प्रीमियम की सदस्यता इस कीमत पर ले रहे हैं","You'll complete payment securely through Razorpay.":"आप Razorpay के माध्यम से सुरक्षित रूप से भुगतान पूरा करेंगे।","Open secure checkout →":"सुरक्षित चेकआउट खोलें →","month":"माह","Launch price":"लॉन्च कीमत","Explore Premium →":"प्रीमियम देखें →","Premium active":"प्रीमियम सक्रिय","Unlock Premium":"प्रीमियम अनलॉक करें","analyses this month":"इस महीने के विश्लेषण"}
}
for _lang, _items in _PREMIUM_LIFECYCLE_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {}).update(_items)


_PREMIUM_FEATURE_I18N = {
"ta": {
"Predictive Risk Engine":"முன்கணிப்பு அபாய இயந்திரம்","Detect likely budget breaches before month-end and calculate a practical daily correction.":"மாத இறுதிக்கு முன் ஏற்படக்கூடிய பட்ஜெட் மீறல்களை கண்டறிந்து, நடைமுறையான தினசரி திருத்தத் தொகையை கணக்கிடுகிறது.","An explainable 0–100 score across savings, budgets, goals and cash-flow stability.":"சேமிப்பு, பட்ஜெட், இலக்குகள் மற்றும் பணப்புழக்க நிலைத்தன்மையை அடிப்படையாகக் கொண்ட விளக்கக்கூடிய 0–100 மதிப்பெண்.","What-if Simulator":"என்ன ஆகும் சிமுலேட்டர்","Model a planned purchase against your recorded savings and goals before you spend.":"செலவழிப்பதற்கு முன் திட்டமிட்ட வாங்குதலை உங்கள் பதிவான சேமிப்புகள் மற்றும் இலக்குகளுடன் ஒப்பிட்டு பார்க்க உதவுகிறது.","AI explanations grounded in Sigora's deterministic financial signals.":"SIGORA-வின் கணக்கிடப்பட்ட நிதிச் சிக்னல்களை அடிப்படையாகக் கொண்ட AI விளக்கங்கள்.","Advanced Reports":"மேம்பட்ட அறிக்கைகள்","Deeper spending, trend and cash-flow analysis.":"செலவு, போக்கு மற்றும் பணப்புழக்கத்தின் ஆழமான பகுப்பாய்வு.","Advanced Goal Intelligence":"மேம்பட்ட இலக்கு நுண்ணறிவு","Connect spending decisions with the goals they can accelerate or delay.":"செலவு முடிவுகள் உங்கள் இலக்குகளை எவ்வாறு விரைவுபடுத்தலாம் அல்லது தாமதப்படுத்தலாம் என்பதை இணைத்துக் காட்டுகிறது.","30 AI analyses / month":"மாதத்திற்கு 30 AI பகுப்பாய்வுகள்","A larger AI allowance with built-in platform safety limits.":"தளத்தின் பாதுகாப்பு வரம்புகளுடன் அதிகமான AI பயன்பாட்டு அளவு."},
"hi": {
"Predictive Risk Engine":"पूर्वानुमान जोखिम इंजन","Detect likely budget breaches before month-end and calculate a practical daily correction.":"महीने के अंत से पहले संभावित बजट उल्लंघन पहचानता है और व्यावहारिक दैनिक सुधार राशि की गणना करता है।","An explainable 0–100 score across savings, budgets, goals and cash-flow stability.":"बचत, बजट, लक्ष्यों और कैश-फ्लो स्थिरता पर आधारित समझाने योग्य 0–100 स्कोर।","What-if Simulator":"क्या-हो-अगर सिमुलेटर","Model a planned purchase against your recorded savings and goals before you spend.":"खर्च करने से पहले नियोजित खरीद को आपकी दर्ज बचत और लक्ष्यों के संदर्भ में देखने में मदद करता है।","AI explanations grounded in Sigora's deterministic financial signals.":"SIGORA के गणना-आधारित वित्तीय संकेतों पर आधारित AI व्याख्याएं।","Advanced Reports":"उन्नत रिपोर्ट","Deeper spending, trend and cash-flow analysis.":"खर्च, रुझान और कैश-फ्लो का गहरा विश्लेषण।","Advanced Goal Intelligence":"उन्नत लक्ष्य इंटेलिजेंस","Connect spending decisions with the goals they can accelerate or delay.":"दिखाता है कि खर्च के फैसले आपके लक्ष्यों को कैसे तेज या धीमा कर सकते हैं।","30 AI analyses / month":"प्रति माह 30 AI विश्लेषण","A larger AI allowance with built-in platform safety limits.":"प्लेटफ़ॉर्म सुरक्षा सीमाओं के साथ अधिक AI उपयोग क्षमता।"}
}
for _lang, _items in _PREMIUM_FEATURE_I18N.items():
    SIGORA_TRANSLATIONS.setdefault(_lang, {}).update(_items)
    SIGORA_PHRASE_TRANSLATIONS.setdefault(_lang, {}).update(_items)

# Production defaults
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("IMPORT_MAX_FILE_MB", "25")) * 1024 * 1024

@app.context_processor
def inject_sigora_globals():
    user = get_current_user()
    currency = (user or {}).get("currency", "INR")
    country = (user or {}).get("country", "India")
    pricing = get_pricing(currency, country)
    symbols = {"INR":"₹","USD":"$","EUR":"€","GBP":"£","CAD":"C$","AUD":"A$","CHF":"CHF","SGD":"S$","AED":"د.إ","JPY":"¥","NZD":"NZ$","ZAR":"R"}
    return {
        "currency_symbol": symbols.get(currency, currency),
        "currency_code": currency,
        "premium_price": pricing["premium_price"],
        "premium_currency_symbol": pricing.get("currency_symbol", "₹"),
        "premium_currency_code": pricing.get("currency", "INR"),
        "support_email": os.getenv("SIGORA_SUPPORT_EMAIL", "").strip(),
        "sigora_countries": COUNTRIES,
        "country_currencies": COUNTRY_CURRENCIES,
        "currency_options": sorted({pair for pair in COUNTRY_CURRENCIES.values()}),
        "ga4_measurement_id": os.getenv("SIGORA_GA4_MEASUREMENT_ID", "").strip(),
        "sigora_language": _sigora_language(),
        "sigora_languages": SIGORA_LANGUAGES,
        "t": _t,
        "sigora_phrase_translations": SIGORA_PHRASE_TRANSLATIONS.get(_sigora_language(), {}),
        "announcement_popup": (
            get_latest_unread_announcement(user["id"], _sigora_language())
            if user and not request.path.startswith("/admin") and request.path != "/announcements" else None
        ),
        "announcement_unread_count": (
            get_unread_announcement_count(user["id"])
            if user and not request.path.startswith("/admin") else 0
        ),
    }

@app.template_filter("money")
def money_filter(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)

def load_transactions():
    transactions = []

    try:
        with open("../Sigora/transaction.csv", "r", newline="") as file:
            reader = csv.DictReader(file)

            for index,row in enumerate(reader, start=1):

                if "id" not in row or not row["id"]:
                    row["id"] = str(index)
                transactions.append(row)

    except FileNotFoundError:
        pass

    return transactions

def save_transactions(transactions):
    with open("../Sigora/transaction.csv", "w", newline="") as file:
        fieldnames = [
            "id",
            "transaction_type",
            "amount",
            "category",
            "description",
            "date"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()

        for transaction in transactions:
            writer.writerow({
                "id": transaction["id"],
                "transaction_type": transaction["transaction_type"],
                "amount": transaction["amount"],
                "category": transaction["category"],
                "description": transaction["description"],
                "date": transaction["date"]
            })

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():

    user = get_current_user()

    if not user:
        return redirect("/login")

    transactions = [convert_transaction(t, user.get("currency", "INR")) for t in get_transactions(user["id"])]

    # ==========================================
    # BASIC FINANCIAL TOTALS
    # ==========================================

    total_income = 0
    total_expense = 0

    for transaction in transactions:

        amount = float(transaction["amount"])

        transaction_type = (
            transaction["transaction_type"]
            .strip()
            .lower()
        )

        if transaction_type == "income":
            total_income += amount

        elif transaction_type == "expense":
            total_expense += amount


    balance = total_income - total_expense

    transaction_count = len(transactions)


    # ==========================================
    # SAVINGS
    # ==========================================

    if total_income > 0:

        savings_rate = (
            (balance / total_income) * 100
        )

    else:

        savings_rate = 0


    # ==========================================
    # LAST TRANSACTION
    # ==========================================

    if transactions:

        last_transaction = max(
            transactions,
            key=lambda transaction: datetime.strptime(
                transaction["date"],
                "%Y-%m-%d"
            )
        )

    else:

        last_transaction = None


    # ==========================================
    # EXPENSE CATEGORY TOTALS
    # ==========================================

    expense_category_totals = {}

    for transaction in transactions:

        if transaction["transaction_type"].strip().lower() != "expense":
            continue

        category = transaction.get("category")

        if not category:
            category = "Other"

        # Normalize category names
        # Food, food, FOOD -> Food
        category = category.strip().title()

        amount = float(transaction["amount"])

        if category in expense_category_totals:

            expense_category_totals[category] += amount

        else:

            expense_category_totals[category] = amount


    # ==========================================
    # TOP EXPENSE CATEGORY
    # ==========================================

    if expense_category_totals:

        top_expense_category = max(
            expense_category_totals,
            key=expense_category_totals.get
        )

        top_amount = (
            expense_category_totals[
                top_expense_category
            ]
        )

    else:

        top_expense_category = None
        top_amount = 0


    # ==========================================
    # SPENDING BREAKDOWN
    # ==========================================

    expense_breakdown = []

    for category, amount in expense_category_totals.items():

        if total_expense > 0:

            percentage = (
                amount / total_expense
            ) * 100

        else:

            percentage = 0


        expense_breakdown.append({

            "category": category,

            "amount": amount,

            "percentage": percentage

        })


    # Largest expenses first
    expense_breakdown.sort(
        key=lambda item: item["amount"],
        reverse=True
    )


    # ==========================================
    # DASHBOARD ALERT
    # ==========================================

    dashboard_alert = None
    dashboard_alert_type = "neutral"

    if not transactions:

        dashboard_alert = (
            "Start by adding your first transaction "
            "to unlock your financial insights."
        )

        dashboard_alert_type = "neutral"


    elif total_income == 0 and total_expense > 0:

        dashboard_alert = (
            "You currently have expenses recorded "
            "but no income recorded. Add your income "
            "to get a clearer picture of your balance."
        )

        dashboard_alert_type = "warning"


    elif balance < 0:

        dashboard_alert = (
            "Your expenses are currently higher than "
            "your recorded income. Review your spending "
            "before taking on additional expenses."
        )

        dashboard_alert_type = "danger"


    elif savings_rate >= 30:

        dashboard_alert = (
            "Strong position — you're currently keeping "
            "a healthy portion of your recorded income."
        )

        dashboard_alert_type = "positive"


    elif savings_rate >= 10:

        dashboard_alert = (
            "You're saving some of your recorded income. "
            "Keep an eye on your largest spending categories "
            "to create more room if needed."
        )

        dashboard_alert_type = "neutral"


    else:

        dashboard_alert = (
            "Your current savings margin is fairly small. "
            "Review your largest discretionary expenses "
            "if you want to create more breathing room."
        )

        dashboard_alert_type = "warning"


    # ==========================================
    # RECENT TRANSACTIONS
    # ==========================================

    recent_transactions = transactions[:5]


    # ==========================================
    # LAUNCH FEATURES
    # ==========================================

    gamification = get_gamification(user["id"])
    current_month = datetime.now().month
    current_year = datetime.now().year
    dashboard_budgets = get_budgets(user["id"], current_month, current_year)
    for budget in dashboard_budgets:
        budget["spent"] = get_budget_spending(user["id"], budget["category"], current_month, current_year)
    dashboard_goals = get_goals(user["id"])

    # Alerts are useful, but must never take the core dashboard down.
    # If a provider/database alert migration fails, Sigora still renders.
    try:
        sync_financial_alerts(user["id"], dashboard_budgets, dashboard_goals)
    except Exception as exc:
        app.logger.exception("Financial alert sync failed: %s", exc)

    try:
        alerts = get_alerts(user["id"], 6, _sigora_language())
    except Exception as exc:
        app.logger.exception("Financial alert load failed: %s", exc)
        alerts = []

    # Signature forward-looking intelligence: deterministic calculations only.
    try:
        intel_context = get_ai_financial_context(user["id"])
        intel_budgets = get_budgets(user["id"], datetime.now().month, datetime.now().year)
        for b in intel_budgets:
            b["spent"] = get_budget_spending(user["id"], b["category"], datetime.now().month, datetime.now().year)
        dashboard_intelligence = build_intelligence(intel_context, intel_budgets, get_goals(user["id"]))
    except Exception as exc:
        app.logger.exception("Dashboard intelligence load failed: %s", exc)
        dashboard_intelligence = {"score_available": False, "forecast_available": False, "projected_expense": None, "projected_savings": None, "risks": [], "headline": _t("not_enough")}

    # ==========================================
    # BALANCE SHEET / NET WORTH
    # ==========================================
    # Account balance is a checkpoint plus subsequent manual activity.
    # Statement closing balances reset the checkpoint, preventing double-counting.
    try:
        account_rows = list_financial_accounts(user["id"])
    except Exception as exc:
        app.logger.exception("Dashboard account balance load failed: %s", exc)
        account_rows = []
    total_cash = 0.0
    total_liabilities = 0.0
    cash_balance_sources = 0
    target_currency = user.get("currency", "INR")
    today = datetime.now().strftime("%Y-%m-%d")
    for account in account_rows:
        raw = account.get("live_balance")
        if raw is None:
            continue
        try:
            value = convert_amount(abs(float(raw)), account.get("currency") or target_currency, target_currency, today)
        except Exception:
            if (account.get("currency") or target_currency) != target_currency:
                continue
            value = abs(float(raw))
        account_type = str(account.get("account_type") or "").lower()
        if account_type in {"credit_card", "loan", "liability", "bnpl"}:
            total_liabilities += value
        else:
            total_cash += max(0.0, float(value))
            cash_balance_sources += 1

    try:
        _portfolio = portfolio_summary(user["id"])
        total_investments = 0.0
        for holding in _portfolio.get("holdings", []):
            hv = float(holding.get("value", 0) or 0)
            try:
                hv = convert_amount(hv, holding.get("currency") or target_currency, target_currency, today)
            except Exception:
                if (holding.get("currency") or target_currency) != target_currency:
                    continue
            total_investments += hv
    except Exception as exc:
        app.logger.exception("Dashboard investment value load failed: %s", exc)
        total_investments = 0.0

    net_worth = total_cash + total_investments - total_liabilities
    now = datetime.now()
    month_transactions = [x for x in transactions if str(x.get("date", "")).startswith(f"{now.year:04d}-{now.month:02d}-")]
    month_income = sum(float(x["amount"]) for x in month_transactions if str(x.get("transaction_type", "")).lower() == "income")
    month_expense = sum(float(x["amount"]) for x in month_transactions if str(x.get("transaction_type", "")).lower() == "expense")

    # ==========================================
    # RENDER
    # ==========================================

    return render_template(

        "dashboard.html",

        user=user,

        transactions=transactions,

        recent_transactions=recent_transactions,

        total_income=total_income,

        total_expense=total_expense,

        balance=balance,

        transaction_count=transaction_count,

        last_transaction=last_transaction,

        expense_category_totals=expense_category_totals,

        expense_breakdown=expense_breakdown,

        top_expense_category=top_expense_category,

        top_amount=top_amount,

        savings_rate=savings_rate,

        dashboard_alert=dashboard_alert,

        dashboard_alert_type=dashboard_alert_type,
        gamification=gamification,
        alerts=alerts,
        dashboard_intelligence=dashboard_intelligence,
        total_cash=total_cash, cash_balance_sources=cash_balance_sources, net_worth_ready=bool(cash_balance_sources), total_investments=total_investments, total_liabilities=total_liabilities, net_worth=net_worth,
        month_income=month_income, month_expense=month_expense

    )

def run_limited_ai(user_id, generator, *args):
    status = get_premium_status(user_id)
    usage = consume_ai_request(user_id, status["is_premium"])
    if not usage["allowed"]:
        if usage["reason"] == "daily":
            return _t("ai_daily_limit_reached").format(limit=usage["daily_limit"])
        if usage["reason"] == "budget":
            return _t("ai_monthly_budget_reached")
        if usage["reason"] == "global":
            return _t("ai_platform_limit_reached")
        return _t("ai_monthly_limit_reached").format(limit=usage["limit"])
    return generator(*args)


@app.route("/transactions")
def transactions():
    user = get_current_user()
    if not user:
        return redirect("/login")

    transactions = [convert_transaction(t, user.get("currency", "INR")) for t in get_transactions(user["id"])]
    search = request.args.get("search", "").strip().lower()
    transaction_type = request.args.get("transaction_type", "all").lower()
    category = request.args.get("category", "all").strip().lower()

    if search:
        transactions = [t for t in transactions if search in str(t.get("transaction_type", "")).lower() or search in str(t.get("description", "")).lower() or search in str(t.get("category", "")).lower()]
    if transaction_type != "all":
        if transaction_type in {"transfer", "transfer_in", "transfer_out"}:
            transactions = [t for t in transactions if str(t.get("transaction_type", "")).lower() in {"transfer_in","transfer_out"}]
            transaction_type = "transfer"
        else:
            transactions = [t for t in transactions if str(t.get("transaction_type", "")).lower() == transaction_type]
    if category != "all":
        transactions = [t for t in transactions if str(t.get("category", "")).lower() == category]

    categories = sorted({str(t.get("category", "Other")).strip().title() for t in get_transactions(user["id"]) if t.get("category")})
    total_income = sum(float(t["amount"]) for t in transactions if str(t["transaction_type"]).lower() == "income")
    total_expense = sum(float(t["amount"]) for t in transactions if str(t["transaction_type"]).lower() == "expense")
    return render_template("transactions.html", transactions=transactions, search=search, transaction_type=transaction_type, category=category, categories=categories, total_income=total_income, total_expense=total_expense, balance=total_income-total_expense)

@app.route("/transactions/export")
def export_transactions():
    user = get_current_user()
    if not user:
        return redirect("/login")
    transactions = [convert_transaction(t, user.get("currency", "INR")) for t in get_transactions(user["id"])]
    search = request.args.get("search", "").strip().lower()
    transaction_type = request.args.get("transaction_type", "all").lower()
    category = request.args.get("category", "all").strip().lower()
    if search:
        transactions = [t for t in transactions if search in str(t.get("transaction_type", "")).lower() or search in str(t.get("description", "")).lower() or search in str(t.get("category", "")).lower()]
    if transaction_type != "all":
        transactions = [t for t in transactions if str(t.get("transaction_type", "")).lower() == transaction_type]
    if category != "all":
        transactions = [t for t in transactions if str(t.get("category", "")).lower() == category]

    fmt = request.args.get("format", "csv").lower()
    rows = [["Date", "Type", "Category", "Description", "Amount"]]
    rows += [[t.get("date", ""), str(t.get("transaction_type", "")).title(), t.get("category", ""), t.get("description", ""), float(t.get("amount", 0))] for t in transactions]
    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Transactions"
        for row in rows: ws.append(row)
        ws.freeze_panes = "A2"
        ws.column_dimensions["A"].width = 14; ws.column_dimensions["B"].width = 12; ws.column_dimensions["C"].width = 20; ws.column_dimensions["D"].width = 40; ws.column_dimensions["E"].width = 16
        out = BytesIO(); wb.save(out); out.seek(0)
        return send_file(out, as_attachment=True, download_name="sigora_transactions.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    out = StringIO(); writer = csv.writer(out); writer.writerows(rows); out.seek(0)
    return send_file(BytesIO(out.getvalue().encode("utf-8-sig")), as_attachment=True, download_name="sigora_transactions.csv", mimetype="text/csv")

@app.route("/delete/<transaction_id>")
def delete_transaction_route(transaction_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    delete_transaction(user["id"], transaction_id)

    return redirect("/transactions")

@app.route("/edit/<transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    transaction = get_transaction(user["id"], transaction_id)

    if not transaction:
        return "Transaction not found", 404


    if request.method == "POST":
       try:
              amount = float(request.form["amount"])

              if amount <= 0:
                   return render_template(
                       "edit_transaction.html",
                       transaction=transaction,
                       error="Amount must be greater than 0."
                   )
       except ValueError:
              return render_template(
                  "edit_transaction.html",
                  transaction=transaction,
                  error="Invalid amount. Please enter a valid number."
              )

       category = request.form["category"].strip()

       if not category:
              return render_template(
                 "edit_transaction.html",
                 transaction=transaction,
                 error="Category cannot be empty."
         )

       description = request.form["description"].strip()

       if not description:
              return render_template(
                "edit_transaction.html",
                transaction=transaction,
                error="Description cannot be empty."
         )

       date = request.form["date"]

       try:
             datetime.strptime(date, "%Y-%m-%d")
       except ValueError:
             return render_template(
              "edit_transaction.html",
              transaction=transaction,
              error="Please enter a valid date."
       )

       update_transaction(
            user["id"],
            transaction_id,
            request.form["transaction_type"],
            amount,
            category,
            description,
            date
    )

       account_id=request.form.get("financial_account_id","").strip()
       assign_transaction_account(user["id"], transaction_id, int(account_id) if account_id else None)
       return redirect("/transactions")

    return render_template("edit_transaction.html", transaction=transaction, accounts=list_financial_accounts(user["id"]))

@app.route("/add-transaction", methods=["GET", "POST"])
def add_transaction():
    user = get_current_user()
    if not user:
        return redirect("/login")
    accounts = list_financial_accounts(user["id"])
    cash_account = next((a for a in accounts if str(a.get("account_type") or "").lower() == "cash"), None)

    if request.method == "POST":
        transaction_type = request.form.get("transaction_type", "expense").strip().lower()
        try:
            amount = float(request.form.get("amount", "0"))
            if amount <= 0: raise ValueError
        except ValueError:
            return render_template("add_transaction.html", error=_t("amount_positive"), accounts=accounts, cash_account=cash_account)
        description = request.form.get("description", "").strip()
        if not description:
            return render_template("add_transaction.html", error=_t("description_required"), accounts=accounts, cash_account=cash_account)
        date = request.form.get("date", "")
        try: datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return render_template("add_transaction.html", error=_t("valid_date_required"), accounts=accounts, cash_account=cash_account)

        if transaction_type == "transfer":
            from_id=request.form.get("from_account_id","").strip(); to_id=request.form.get("to_account_id","").strip()
            try:
                if from_id == "__cash__":
                    raw=request.form.get("cash_opening_balance","").strip()
                    opening=float(raw.replace(",","")) if raw else None
                    from_id=str(get_or_create_physical_cash_account(user["id"], user.get("currency","INR"), opening))
                if to_id == "__cash__":
                    raw=request.form.get("cash_opening_balance","").strip()
                    opening=float(raw.replace(",","")) if raw else None
                    to_id=str(get_or_create_physical_cash_account(user["id"], user.get("currency","INR"), opening))
                if not from_id or not to_id: raise ValueError(_t("transfer_accounts_required"))
                create_transfer(user["id"], amount, int(from_id), int(to_id), description, date)
            except (ValueError, TypeError) as exc:
                accounts=list_financial_accounts(user["id"]); cash_account=next((a for a in accounts if a.get("account_type")=="cash"),None)
                return render_template("add_transaction.html", error=str(exc), accounts=accounts, cash_account=cash_account)
            award_activity(user["id"], "transaction", 10)
            return redirect("/transactions")

        if transaction_type not in {"income","expense"}:
            return render_template("add_transaction.html", error=_t("valid_transaction_type"), accounts=accounts, cash_account=cash_account)
        category=request.form.get("category","").strip()
        if not category or category.lower() in {"auto","auto-categorize","automatic"}:
            category=categorize_transaction(description,transaction_type)
        account_choice=request.form.get("financial_account_id","").strip()
        account_id=None
        try:
            if account_choice == "__cash__":
                raw=request.form.get("cash_opening_balance","").strip()
                opening=float(raw.replace(",","")) if raw else None
                account_id=get_or_create_physical_cash_account(user["id"],user.get("currency","INR"),opening)
            elif account_choice:
                account_id=int(account_choice)
                if not get_financial_account(user["id"],account_id): raise ValueError(_t("choose_valid_account"))
        except (ValueError,TypeError) as exc:
            return render_template("add_transaction.html", error=str(exc), accounts=accounts, cash_account=cash_account)
        db_add_transaction(user["id"],transaction_type,amount,category,description,date,financial_account_id=account_id)
        award_activity(user["id"],"transaction",10)
        return redirect("/transactions")

    return render_template("add_transaction.html", accounts=accounts, cash_account=cash_account)

@app.route("/budgets")
def budgets():

    user = get_current_user()

    if not user:
        return redirect("/login")


    # =================================================
    # CURRENT MONTH
    # =================================================

    now = datetime.now()

    month = now.month
    year = now.year


    # =================================================
    # GET BUDGETS
    # =================================================

    budgets = get_budgets(
        user["id"],
        month,
        year
    )


    # =================================================
    # GET EXPENSE CATEGORIES
    # =================================================

    expense_categories = get_expense_categories(
        user["id"]
    )


    # =================================================
    # PROCESS BUDGETS
    # =================================================

    for budget in budgets:

        # ---------------------------------------------
        # CURRENT SPENDING
        # ---------------------------------------------

        spent = get_budget_spending(
            user["id"],
            budget["category"],
            month,
            year
        )


        # ---------------------------------------------
        # REMAINING
        # ---------------------------------------------

        remaining = (
            budget["amount"] - spent
        )


        # ---------------------------------------------
        # PERCENTAGE USED
        # ---------------------------------------------

        percentage_used = (
            (spent / budget["amount"]) * 100
            if budget["amount"] > 0
            else 0
        )


        # ---------------------------------------------
        # STORE CALCULATED VALUES
        # ---------------------------------------------

        budget["spent"] = spent

        budget["remaining"] = remaining

        budget["percentage_used"] = (
            percentage_used
        )


        # ---------------------------------------------
        # STATUS
        # ---------------------------------------------

        if percentage_used >= 100:

            budget["status"] = "Over"

        elif percentage_used >= 75:

            budget["status"] = "Warning"

        else:

            budget["status"] = "Good"


        # ---------------------------------------------
        # BUDGET AI
        # ---------------------------------------------

        requested_ai_budget = request.args.get("ai_budget", type=int)
        budget["ai_insight"] = None
        if requested_ai_budget == budget.get("id"):
            budget["ai_insight"] = run_limited_ai(user["id"], get_budget_ai_insight, budget, expense_categories)


    # =================================================
    # RENDER
    # =================================================

    return render_template(
        "budgets.html",
        budgets=budgets,
        month=month,
        year=year
    )

@app.route("/add-budget", methods=["GET", "POST"])
def add_budget_route():

    user = get_current_user()

    if not user:
        return redirect("/login")

    if request.method == "POST":

        category = request.form["category"].strip()

        if not category:
            return render_template(
                "add_budget.html",
                error="Category cannot be empty."
            )

        try:
            amount = float(request.form["amount"])

            if amount <= 0:
                return render_template(
                    "add_budget.html",
                    error="Budget amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "add_budget.html",
                error="Please enter a valid budget amount."
            )

        month = int(request.form["month"])
        year = int(request.form["year"])

        if month < 1 or month > 12:
            return render_template(
                "add_budget.html",
                error="Please select a valid month."
            )

        if year < 2000:
            return render_template(
                "add_budget.html",
                error="Please enter a valid year."
            )

        budget_id=add_budget(
            user["id"],
            category,
            amount,
            month,
            year,
            user.get("currency", "INR")
        )

        if budget_id is None:

             return render_template(
                    "add_budget.html",
                    current_month=month,
                    current_year=year,
                    error=f"You already have a {category.title()} budget for this month."
                )


        award_activity(user["id"], "budget", 20)
        return redirect("/budgets?celebration=budget")

    now = datetime.now()

    return render_template(
        "add_budget.html",
        current_month=now.month,
        current_year=now.year
    )

@app.route("/delete-budget/<budget_id>")
def delete_budget_route(budget_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    delete_budget(
        user["id"],
        budget_id
    )

    return redirect("/budgets")

@app.route("/edit-budget/<budget_id>", methods=["GET", "POST"])
def edit_budget(budget_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    now = datetime.now()

    budgets = get_budgets(
        user["id"],
        now.month,
        now.year
    )

    budget = None

    for item in budgets:
        if str(item["id"]) == str(budget_id):
            budget = item
            break

    if budget is None:
        return "Budget not found", 404

    if request.method == "POST":

        category = request.form["category"].strip()

        if not category:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Category cannot be empty."
            )

        try:
            amount = float(request.form["amount"])

            if amount <= 0:
                return render_template(
                    "edit_budget.html",
                    budget=budget,
                    error="Budget amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please enter a valid budget amount."
            )

        try:
            month = int(request.form["month"])
            year = int(request.form["year"])

        except ValueError:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please enter a valid month and year."
            )

        if month < 1 or month > 12:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please select a valid month."
            )

        if year < 2000:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please enter a valid year."
            )

        update_budget(
            user["id"],
            budget_id,
            category,
            amount,
            month,
            year,
            user.get("currency", "INR")
        )
        award_activity(user["id"], "budget", 10)
        return redirect("/budgets?celebration=budget")

    return render_template(
        "edit_budget.html",
        budget=budget
    )

@app.route("/goals")
def goals():

    user = get_current_user()

    if not user:
        return redirect("/login")

    # =================================================
    # GET GOALS
    # =================================================

    goals = get_goals(user["id"])

    # =================================================
    # GET MONTHLY SAVINGS
    # =================================================

    monthly_savings = get_monthly_savings(user["id"])

    positive_savings = [
        month["savings"]
        for month in monthly_savings
        if month["savings"] > 0
    ]

    if positive_savings:

        average_monthly_saving = (
            sum(positive_savings)
            / len(positive_savings)
        )

    else:

        average_monthly_saving = 0

    # =================================================
    # GET EXPENSE CATEGORIES
    # =================================================

    expense_categories = get_expense_categories(
        user["id"]
    )

    # =================================================
    # CURRENT DATE
    # =================================================

    today = datetime.now().date()

    # =================================================
    # PROCESS EACH GOAL
    # =================================================

    for goal in goals:

        target_amount = float(
            goal["target_amount"]
        )

        current_amount = float(
            goal["current_amount"]
        )

        # ---------------------------------------------
        # REMAINING AMOUNT
        # ---------------------------------------------

        remaining = max(
            target_amount - current_amount,
            0
        )

        # ---------------------------------------------
        # TARGET DATE
        # ---------------------------------------------

        target_date = datetime.strptime(
            str(goal["target_date"]),
            "%Y-%m-%d"
        ).date()

        days_remaining = (
            target_date - today
        ).days

        # ---------------------------------------------
        # GOAL STATUS
        # ---------------------------------------------

        if remaining <= 0:

            required_monthly_saving = 0

            likelihood = "Completed"

        elif days_remaining <= 0:

            required_monthly_saving = remaining

            likelihood = "Missed"

        else:

            months_remaining = max(
                days_remaining / 30.44,
                1
            )

            required_monthly_saving = (
                remaining / months_remaining
            )

            if average_monthly_saving <= 0:

                likelihood = "Low"

            elif (
                average_monthly_saving
                >= required_monthly_saving
            ):

                likelihood = "High"

            elif (
                average_monthly_saving
                >= required_monthly_saving * 0.7
            ):

                likelihood = "Medium"

            else:

                likelihood = "Low"

        # ---------------------------------------------
        # ADD CALCULATED VALUES
        # ---------------------------------------------

        goal["remaining"] = remaining

        goal["required_monthly_saving"] = (
            required_monthly_saving
        )

        goal["average_monthly_saving"] = (
            average_monthly_saving
        )

        goal["likelihood"] = likelihood

        # ---------------------------------------------
        # GOAL AI
        # ---------------------------------------------

        requested_ai_goal = request.args.get("ai_goal", type=int)
        goal["ai_insight"] = None
        if requested_ai_goal == goal.get("id"):
            goal["ai_insight"] = run_limited_ai(user["id"], get_goal_ai_insight, goal, expense_categories)

    # =================================================
    # RENDER PAGE
    # =================================================

    return render_template(
        "goals.html",
        goals=goals
    )


@app.route("/add-goal", methods=["GET", "POST"])
def add_goal_route():

    user = get_current_user()

    if not user:
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"].strip()

        if not name:
            return render_template(
                "add_goal.html",
                error="Goal name cannot be empty."
            )

        try:
            target_amount = float(request.form["target_amount"])

            if target_amount <= 0:
                return render_template(
                    "add_goal.html",
                    error="Target amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "add_goal.html",
                error="Please enter a valid target amount."
            )

        try:
            current_amount = float(request.form["current_amount"])

            if current_amount < 0:
                return render_template(
                    "add_goal.html",
                    error="Current amount cannot be negative."
                )

            if current_amount > target_amount:
                return render_template(
                    "add_goal.html",
                    error="Current amount cannot be greater than the target."
                )

        except ValueError:
            return render_template(
                "add_goal.html",
                error="Please enter a valid current amount."
            )

        target_date = request.form["target_date"]

        try:
            datetime.strptime(target_date, "%Y-%m-%d")

        except ValueError:
            return render_template(
                "add_goal.html",
                error="Please enter a valid target date."
            )

        goal_id=add_goal(
            user["id"],
            name,
            target_amount,
            current_amount,
            target_date,
            user.get("currency", "INR")
        )

        if goal_id is None:

         return render_template(
                "add_goal.html",
                error="You already have this goal.",
            )

        award_activity(user["id"], "goal", 25)
        return redirect("/goals?celebration=goal")

    return render_template("add_goal.html")

@app.route("/edit-goal/<goal_id>", methods=["GET", "POST"])
def edit_goal(goal_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    goals = get_goals(user["id"])

    goal = None

    for item in goals:
        if str(item["id"]) == str(goal_id):
            goal = item
            break

    if goal is None:
        return "Goal not found", 404

    if request.method == "POST":

        name = request.form["name"].strip()

        if not name:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Goal name cannot be empty."
            )

        try:
            target_amount = float(request.form["target_amount"])

            if target_amount <= 0:
                return render_template(
                    "edit_goal.html",
                    goal=goal,
                    error="Target amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Please enter a valid target amount."
            )

        try:
            current_amount = float(request.form["current_amount"])

            if current_amount < 0:
                return render_template(
                    "edit_goal.html",
                    goal=goal,
                    error="Current amount cannot be negative."
                )

            if current_amount > target_amount:
                return render_template(
                    "edit_goal.html",
                    goal=goal,
                    error="Current amount cannot be greater than the target."
                )

        except ValueError:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Please enter a valid current amount."
            )

        target_date = request.form["target_date"]

        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Please enter a valid target date."
            )

        was_completed = float(goal["current_amount"]) >= float(goal["target_amount"])
        update_goal(
            user["id"],
            goal_id,
            name,
            target_amount,
            current_amount,
            target_date,
            user.get("currency", "INR")
        )
        award_activity(user["id"], "goal", 10)
        celebration = "goal-complete" if (current_amount >= target_amount and not was_completed) else "goal"
        if current_amount >= target_amount and not was_completed:
            award_activity(user["id"], "goal_completed", 75)
        return redirect(f"/goals?celebration={celebration}")

    return render_template(
        "edit_goal.html",
        goal=goal
    )

@app.route("/goals/<goal_id>/add-savings", methods=["POST"])
def add_goal_savings_route(goal_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    try:
        amount = float(request.form.get("amount", ""))
    except (ValueError, TypeError):
        return redirect("/goals?error=invalid-savings")

    if amount <= 0:
        return redirect("/goals?error=invalid-savings")

    result = add_goal_savings(
        user["id"],
        goal_id,
        amount
    )

    if result is None:
        return redirect("/goals?error=goal-not-found")

    award_activity(user["id"], "goal", 10)

    # If the added amount completes the goal, award the completion activity once.
    if float(result[3]) >= float(result[2]):
        award_activity(user["id"], "goal_completed", 75)
        return redirect("/goals?celebration=goal-complete")

    return redirect("/goals?celebration=goal")


@app.route("/delete-goal/<goal_id>")
def delete_goal_route(goal_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    delete_goal(
        user["id"],
        goal_id
    )

    return redirect("/goals")

@app.route("/reports")
def reports():

    user = get_current_user()

    if not user:
        return redirect("/login")

    report = get_report_totals(user["id"])
    monthly_report = get_monthly_report(user["id"])
    category_report = get_expense_categories_by_period(user["id"])

    balance = (
        report["total_income"]
        - report["total_expense"]
    )

    return render_template(
        "reports.html",
        report=report,
        balance=balance,
        monthly_report = monthly_report,
        category_report = category_report
    )

@app.route("/signup", methods=["GET", "POST"])
def signup():
    ensure_feature_schema()
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            return render_template(
                "signup.html",
                error="Please fill in all fields."
            )

        existing_user = get_user_by_email(email)

        if existing_user:
            return render_template(
                "signup.html",
                error="An account with this email already exists."
            )

        country = request.form.get("country", "India").strip()
        if country not in COUNTRY_CURRENCIES:
            country = "India"
        currency, _ = currency_for_country(country)
        user_id = create_user(name, email, password, currency=currency, country=country)
        session["user_id"] = user_id
        return redirect("/dashboard")

    return render_template("signup.html", countries=COUNTRIES)

@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_feature_schema()
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = get_user_by_email(email)

        if not user:
            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        if not check_user_password(
            password,
            user["password_hash"]
        ):
            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        access = get_user_access_state(user["id"])
        if access and access.get("account_status") != "active":
            return render_template(
                "login.html",
                error="This account is currently unavailable. Please contact Sigora support."
            )
        if access and access.get("role") in {"super_admin", "admin", "support"}:
            return redirect("/admin/login")

        session["user_id"] = user["id"]
        touch_last_login(user["id"])

        return redirect("/dashboard")

    return render_template("login.html", changed=request.args.get("changed"))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    ensure_feature_schema()
    message = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_user_by_email(email) if email else None
        if user:
            token = create_password_reset_token(user["id"], ttl_minutes=30)
            if token:
                base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/")
                reset_url = f"{base_url}/reset-password/{token}"
                support_email = os.getenv("SIGORA_SUPPORT_EMAIL", "support.sigora@gmail.com").strip()
                body = (
                    f"Hi {user['name']},\n\n"
                    "We received a request to reset your Sigora password.\n\n"
                    f"Reset your password: {reset_url}\n\n"
                    "This link expires in 30 minutes and can only be used once. "
                    "If you did not request this, you can ignore this email; your password will stay unchanged.\n\n"
                    f"Need help? Contact {support_email}.\n\n"
                    "— Sigora"
                )
                send_transactional_email(user["email"], "Reset your Sigora password", body)
        message = "If an account exists for that email, a password reset link has been sent. Please check your inbox and spam folder."
    return render_template("forgot_password.html", message=message)

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    ensure_feature_schema()
    valid = password_reset_token_is_valid(token)
    error = None
    if request.method == "POST":
        if not valid:
            error = "This password reset link is invalid or has expired. Please request a new one."
        else:
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            if len(password) < 8:
                error = "Password must be at least 8 characters."
            elif password != confirm_password:
                error = "Passwords do not match."
            else:
                password_hash = generate_password_hash(password, method="pbkdf2:sha256")
                if reset_password_with_token(token, password_hash):
                    session.clear()
                    return redirect("/login?changed=1")
                error = "This password reset link is invalid or has expired. Please request a new one."
                valid = False
    return render_template("reset_password.html", token=token, valid=valid, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/accounts")
def accounts():
    user = get_current_user()
    if not user:
        return redirect("/login")
    return render_template("accounts.html", accounts=list_financial_accounts(user["id"]), connections=list_bank_connections(user["id"]), setu_configured=setu_configured(), message=request.args.get("message"), error=request.args.get("error"))



@app.route("/accounts/<int:account_id>")
def account_detail(account_id):
    user=get_current_user()
    if not user: return redirect("/login")
    account=get_financial_account(user["id"],account_id)
    if not account: return redirect("/accounts?error=Account not found.")
    activity=get_financial_account_activity(user["id"],account_id,150)
    return render_template("account_detail.html",account=account,activity=activity,message=request.args.get("message"),error=request.args.get("error"))

@app.route("/accounts/add", methods=["POST"])
def add_statement_account():
    user = get_current_user()
    if not user:
        return redirect("/login")
    account_type = request.form.get("account_type", "savings").strip().lower()
    if account_type not in {"savings","current","cash","wallet","credit_card","loan","liability"}:
        return redirect("/accounts?error=Choose a valid account type.")
    institution = request.form.get("institution_name", "").strip()
    if account_type == "cash": institution = "Cash"
    if not institution:
        return redirect("/accounts?error=Enter the bank, wallet or institution name.")
    name = request.form.get("account_name", "").strip() or ("Physical Cash" if account_type == "cash" else institution)
    currency = request.form.get("currency", user.get("currency", "INR")).strip().upper()
    masked = request.form.get("masked_account", "").strip()[-8:] or None
    raw_balance = request.form.get("balance", "").strip()
    try:
        balance = float(raw_balance.replace(",", "")) if raw_balance else None
    except ValueError:
        return redirect("/accounts?error=Balance must be a number.")
    duplicate = find_duplicate_manual_financial_account(user["id"], institution, name, account_type, masked)
    if duplicate:
        return redirect("/accounts?error=That exact account already exists. Use a different nickname or last 4 digits for another account at the same bank.")
    create_manual_financial_account(user["id"], institution, name, account_type, currency, masked, balance)
    return redirect("/accounts?message=Account added. Import a statement to fill it with transactions.")

@app.route("/accounts/<int:account_id>/edit", methods=["POST"])
def edit_financial_account(account_id):
    user=get_current_user()
    if not user: return redirect("/login")
    current=get_financial_account(user["id"],account_id)
    if not current: return redirect("/accounts?error=Account not found.")
    institution=request.form.get("institution_name","").strip()
    name=request.form.get("account_name","").strip() or institution
    typ=request.form.get("account_type","savings").strip().lower()
    currency=request.form.get("currency","INR").strip().upper()
    masked=request.form.get("masked_account","").strip()[-8:] or None
    raw=request.form.get("balance","").strip()
    try: balance=float(raw.replace(",","")) if raw else None
    except ValueError: return redirect(f"/accounts/{account_id}?error=Balance must be a number.")
    duplicate=find_duplicate_manual_financial_account(user["id"],institution,name,typ,masked)
    if duplicate and duplicate != account_id: return redirect(f"/accounts/{account_id}?error=That exact account already exists.")
    update_financial_account(user["id"],account_id,institution,name,typ,currency,masked,balance)
    return redirect(f"/accounts/{account_id}?message=Account updated.")

@app.route("/accounts/<int:account_id>/delete", methods=["POST"])
def remove_financial_account(account_id):
    user=get_current_user()
    if not user: return redirect("/login")
    delete_financial_account(user["id"],account_id)
    return redirect("/accounts?message=Account removed. Existing transactions were kept as unassigned.")

@app.route("/accounts/connect/india", methods=["POST"])
def connect_india_account():
    user = get_current_user()
    if not user:
        return redirect("/login")
    if not setu_configured():
        return redirect("/accounts?error=Indian bank connectivity is not activated yet. Complete Setu Account Aggregator onboarding and add the production credentials in Render.")
    mobile = request.form.get("mobile", "").strip()
    try:
        callback = request.url_root.rstrip("/") + "/accounts"
        consent = create_consent(mobile, callback)
        consent_id = consent.get("id") or consent.get("consentId")
        consent_url = consent.get("url") or consent.get("webviewUrl")
        if not consent_id or not consent_url:
            raise RuntimeError("Setu did not return a consent URL. Please check the Setu product configuration.")
        create_bank_connection(user["id"], "setu_aa", consent_id, "pending")
        return redirect(consent_url)
    except Exception as exc:
        app.logger.exception("Setu consent creation failed")
        return redirect("/accounts?error=" + requests.utils.quote(str(exc)[:240]))


@app.route("/accounts/sync/<consent_id>", methods=["POST"])
def sync_india_account(consent_id):
    user = get_current_user()
    if not user:
        return redirect("/login")
    connection = get_bank_connection(user["id"], consent_id)
    if not connection:
        return redirect("/accounts?error=Connection not found.")
    try:
        consent = get_consent(consent_id)
        status = str(consent.get("status", "")).upper()
        if status in {"REJECTED", "REVOKED", "EXPIRED", "PAUSED"}:
            update_bank_connection(user["id"], consent_id, status.lower())
            return redirect("/accounts?error=" + requests.utils.quote(f"Bank consent status is {status.lower()}"))
        if status not in {"ACTIVE", "APPROVED"}:
            update_bank_connection(user["id"], consent_id, status.lower() or "pending")
            return redirect("/accounts?message=Your bank consent is still waiting for approval or account data.")
        now = datetime.utcnow()
        start = datetime(now.year - 2, now.month, now.day).isoformat() + "Z"
        end = now.isoformat() + "Z"
        session_data = create_session(consent_id, start, end)
        session_id = session_data.get("id") or session_data.get("dataSessionId")
        update_bank_connection(user["id"], consent_id, "fetching", session_id)
        if not session_id:
            return redirect("/accounts?message=Bank connection started. Sigora is waiting for transaction data.")
        fetched = get_session(session_id)
        status2 = str(fetched.get("status", "")).upper()
        if status2 not in {"PARTIAL", "COMPLETED"}:
            return redirect("/accounts?message=Bank connection is waiting for the bank to provide transaction data. Try sync again shortly.")
        imported = 0
        parsed_accounts = parse_accounts(fetched)
        account_ids = []
        for item in parsed_accounts:
            account_ids.append(upsert_financial_account(user["id"], "setu_aa", item["institution_name"], item["account"], "India", item["currency"]))
        parsed = parse_transactions(fetched)
        for tx in parsed:
            result = import_external_transaction(user["id"], tx, account_ids[0] if account_ids else None)
            if result.get("created"):
                imported += 1
        update_bank_connection(user["id"], consent_id, "connected", session_id, True)
        return redirect("/accounts?message=" + requests.utils.quote(f"Bank sync complete. {imported} new transaction(s) imported."))
    except Exception as exc:
        app.logger.exception("Setu sync failed")
        return redirect("/accounts?error=" + requests.utils.quote(str(exc)[:240]))


@app.route("/webhooks/setu/aa", methods=["POST"])
def setu_aa_webhook():
    payload = request.get_json(silent=True) or {}
    consent_id = payload.get("consentId")
    if not consent_id:
        return jsonify({"success": True})

    connection = get_bank_connection_by_consent(consent_id)
    if not connection:
        # Unknown consent IDs are ignored and never create user data.
        return jsonify({"success": True})

    user_id = connection["user_id"]
    event_type = str(payload.get("type") or "").upper()
    status_raw = str((payload.get("data") or {}).get("status") or payload.get("status") or "pending").upper()
    update_bank_connection(user_id, consent_id, status_raw.lower())

    try:
        fetched = None
        data_session_id = payload.get("dataSessionId")

        # Current Setu Auto-Fetch can deliver decrypted FI data directly in the webhook.
        if event_type == "FI_DATA_READY" and payload.get("fiData"):
            fetched = payload
        # Standard data-session notifications require a follow-up authenticated fetch.
        elif event_type == "SESSION_STATUS_UPDATE" and status_raw in {"PARTIAL", "COMPLETED"} and data_session_id:
            fetched = get_session(data_session_id)

        if fetched:
            account_by_mask = {}
            first_account_id = None
            for item in parse_accounts(fetched):
                aid = upsert_financial_account(user_id, "setu_aa", item["institution_name"], item["account"], "India", item["currency"])
                if first_account_id is None:
                    first_account_id = aid
                masked = str(item["account"].get("maskedAccNumber") or "")
                if masked:
                    account_by_mask[masked] = aid

            for tx in parse_transactions(fetched):
                aid = account_by_mask.get(str(tx.get("account_masked") or ""), first_account_id)
                import_external_transaction(user_id, tx, aid)

            update_bank_connection(user_id, consent_id, "connected", data_session_id, True)
    except Exception:
        app.logger.exception("Automatic Setu transaction ingestion failed")

    return jsonify({"success": True})


@app.route("/language", methods=["POST"])
def set_language():
    lang = request.form.get("language", "en").strip().lower()
    if lang in SIGORA_LANGUAGES:
        session["sigora_language"] = lang
    target = request.form.get("next") or request.referrer or "/dashboard"
    if not str(target).startswith("/"):
        target = "/dashboard"
    return redirect(target)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    user = get_current_user()
    if not user:
        return redirect("/login")

    settings_data = get_user_settings(user["id"])
    error = None

    if request.method == "POST":
        action = request.form.get("action", "preferences")

        if action == "preferences":
            name = request.form.get("name", "").strip()
            country = request.form.get("country", "India").strip()[:100]
            requested_currency = request.form.get("currency", "").strip().upper()[:10]
            allowed_currencies = {code for code, _symbol in COUNTRY_CURRENCIES.values()}
            if country in COUNTRY_CURRENCIES:
                currency = requested_currency or currency_for_country(country)[0]
            else:
                currency = requested_currency or "INR"

            if currency not in allowed_currencies:
                error = "Please select a supported currency."
            elif not name:
                error = "Name cannot be empty."
            else:
                try:
                    update_user_settings(
                        user["id"], name, currency, country or "India",
                        request.form.get("notification_email_enabled") == "on",
                        request.form.get("budget_alerts_enabled") == "on",
                        request.form.get("goal_alerts_enabled") == "on",
                        request.form.get("ai_alerts_enabled") == "on",
                    )
                    return redirect("/settings?saved=1")
                except RuntimeError as exc:
                    # FX availability should never produce the generic 500 page.
                    error = str(exc)

        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            if not check_user_password(current_password, user["password_hash"]):
                error = "Current password is incorrect."
            elif len(new_password) < 8:
                error = "New password must be at least 8 characters."
            elif new_password != confirm_password:
                error = "New passwords do not match."
            else:
                change_user_password(user["id"], generate_password_hash(new_password, method="pbkdf2:sha256"))
                session.clear()
                return redirect("/login?changed=1")

        elif action == "delete_account":
            delete_user_account(user["id"])
            session.clear()
            return redirect("/?deleted=1")

        elif action == "support":
            support_email = request.form.get("email", "").strip().lower()
            issue_type = request.form.get("issue_type", "General question").strip()
            message = request.form.get("message", "").strip()
            if not support_email or "@" not in support_email or not message:
                error = "Please enter a valid email and a message."
            else:
                submit_support_message(user["id"], settings_data["name"], support_email, issue_type, message)
                return redirect("/settings?support=sent")

    settings_data = get_user_settings(user["id"])
    return render_template("settings.html", settings=settings_data, premium_features=premium_features(), error=error)


@app.route("/announcements")
def announcements():
    user = get_current_user()
    if not user:
        return redirect("/login")
    items = get_user_announcements(user["id"], _sigora_language(), 100)
    return render_template("announcements.html", announcements=items)


@app.route("/alerts/<int:alert_id>/read", methods=["POST"])
def read_alert(alert_id):
    user = get_current_user()
    if not user:
        return redirect("/login")
    mark_alert_read(user["id"], alert_id)
    return redirect(request.form.get("next") or "/dashboard")


@app.route("/announcements/<int:alert_id>/clear", methods=["POST"])
def clear_announcement_for_user(alert_id):
    user = get_current_user()
    if not user:
        return redirect("/login")
    clear_user_announcement(user["id"], alert_id)
    return redirect("/announcements?cleared=1")


@app.route("/announcements/clear-read", methods=["POST"])
def clear_read_announcements_for_user():
    user = get_current_user()
    if not user:
        return redirect("/login")
    removed = clear_read_user_announcements(user["id"])
    return redirect(f"/announcements?cleared_read={removed}")


@app.route("/premium/subscribe", methods=["POST"])
def premium_subscribe():
    user = get_current_user()
    if not user:
        return redirect("/login")
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    pricing = get_pricing(user.get("currency", "INR"), user.get("country", "India"))
    plan_id = pricing.get("plan_id")
    coupon_code = request.form.get("coupon_code","").strip().upper()
    coupon = None
    if coupon_code:
        from product_features import validate_coupon
        coupon = validate_coupon(coupon_code, user["id"])
        if not coupon.get("valid"):
            return redirect("/premium?payment=coupon_error")
    if not all([key_id, key_secret, plan_id]):
        return redirect("/premium?payment=not_configured")
    try:
        subscription_payload = {
            "plan_id": plan_id,
            "total_count": int(os.getenv("RAZORPAY_TOTAL_COUNT", "120")),
            "customer_notify": True,
            "notes": {"user_id": str(user["id"]), "product": "Sigora Premium", "coupon_code": coupon_code or "", "billing_currency": pricing["currency"]},
        }
        if coupon and coupon.get("razorpay_offer_id"):
            subscription_payload["offer_id"] = coupon["razorpay_offer_id"]
        response = requests.post(
            "https://api.razorpay.com/v1/subscriptions",
            auth=(key_id, key_secret),
            json=subscription_payload,
            timeout=15,
        )
        if not response.ok:
            try:
                razorpay_error = response.json().get("error", {})
                error_code = razorpay_error.get("code", "unknown")
                error_description = razorpay_error.get("description", "Razorpay rejected the subscription request")
            except Exception:
                error_code = "unknown"
                error_description = "Razorpay rejected the subscription request"
            app.logger.error(
                "Razorpay subscription creation failed: status=%s code=%s description=%s",
                response.status_code, error_code, error_description
            )
            return redirect("/premium?payment=provider_error")
        data = response.json()
        subscription_id = data.get("id")
        if subscription_id and coupon:
            remember_subscription_coupon(subscription_id, coupon["id"], user["id"])
        if subscription_id:
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET razorpay_subscription_id=%s WHERE id=%s", (subscription_id, user["id"]))
                conn.commit()
            finally:
                conn.close()
        return render_template("premium_checkout.html", key_id=key_id, subscription=data)
    except Exception as exc:
        print("RAZORPAY SUBSCRIPTION ERROR:", repr(exc))
        return redirect("/premium?payment=error")


@app.route("/razorpay/verify", methods=["POST"])
def razorpay_verify():
    user = get_current_user()
    if not user:
        return jsonify({"ok": False, "error": "Login required"}), 401
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    data = request.get_json(silent=True) or {}
    payment_id = data.get("razorpay_payment_id", "")
    subscription_id = data.get("razorpay_subscription_id", "")
    signature = data.get("razorpay_signature", "")
    if not all([key_secret, payment_id, subscription_id, signature]):
        return jsonify({"ok": False, "error": "Missing payment verification fields"}), 400
    expected = hmac.new(key_secret.encode(), f"{payment_id}|{subscription_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return jsonify({"ok": False, "error": "Invalid payment signature"}), 400
    if get_user_id_for_subscription(subscription_id) != user["id"]:
        return jsonify({"ok": False, "error": "Subscription does not belong to this account"}), 403
    record_payment_event("checkout.signature_verified", user_id=user["id"], payment_id=payment_id, subscription_id=subscription_id, status="verified", source="client_verify")
    return jsonify({"ok": True})


@app.route("/premium/cancel", methods=["POST"])
def premium_cancel():
    user = get_current_user()
    if not user:
        return redirect("/login")
    subscription_id = get_razorpay_subscription_id(user["id"])
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not all([subscription_id, key_id, key_secret]):
        return redirect("/premium?cancel=not_configured")
    try:
        response = requests.post(
            f"https://api.razorpay.com/v1/subscriptions/{subscription_id}/cancel",
            auth=(key_id, key_secret), json={"cancel_at_cycle_end": True}, timeout=15
        )
        response.raise_for_status()
        cancel_data = response.json() if response.content else {}
        cancel_end = None
        if cancel_data.get("current_end"):
            try:
                cancel_end = datetime.utcfromtimestamp(int(cancel_data["current_end"]))
            except (ValueError, TypeError, OSError):
                cancel_end = None
        # cancel_at_cycle_end stops renewal, not already-paid access.
        # Preserve the entitlement immediately from Razorpay's authoritative current_end.
        if cancel_end and cancel_end > datetime.utcnow():
            from product_features import set_premium_status
            set_premium_status(user["id"], True, cancel_end, cancel_data.get("status"))
        mark_subscription_cancellation_requested(user["id"], True)
        return redirect("/premium?cancel=requested")
    except Exception as exc:
        print("RAZORPAY CANCEL ERROR:", repr(exc))
        return redirect("/premium?cancel=error")


@app.route("/razorpay/webhook", methods=["POST"])
def razorpay_webhook():
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        return jsonify({"ok": False, "error": "Webhook secret not configured"}), 503
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return jsonify({"ok": False, "error": "Invalid signature"}), 400
    payload = request.get_json(silent=True) or {}
    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    subscription_id = entity.get("id") or payment_entity.get("subscription_id")
    notes = entity.get("notes") or payment_entity.get("notes") or {}
    user_id = notes.get("user_id") or (get_user_id_for_subscription(subscription_id) if subscription_id else None)
    amount_raw = payment_entity.get("amount")
    amount = (float(amount_raw) / 100.0) if isinstance(amount_raw, (int, float)) else None
    record_payment_event(event or "razorpay.webhook", user_id=int(user_id) if user_id else None,
                         payment_id=payment_entity.get("id"), order_id=payment_entity.get("order_id"),
                         subscription_id=subscription_id, amount=amount, currency=payment_entity.get("currency"),
                         status=payment_entity.get("status") or entity.get("status"), source="webhook")
    if not user_id:
        return jsonify({"ok": True})
    active_events = {"subscription.activated", "subscription.charged"}
    # Razorpay can cancel at cycle end. A cancellation event must not remove
    # access before current_end if a paid period is still in progress.
    terminal_events = {"subscription.halted", "subscription.completed"}
    expires_at = None
    if entity.get("current_end"):
        try:
            expires_at = datetime.utcfromtimestamp(int(entity["current_end"]))
        except (ValueError, TypeError, OSError):
            expires_at = None
    if event in active_events:
        from product_features import set_premium_status
        set_premium_status(int(user_id), True, expires_at, entity.get("status"))
        if event == "subscription.activated":
            mark_subscription_cancellation_requested(int(user_id), False)
        if subscription_id:
            redeem_subscription_coupon(subscription_id)
    elif event == "subscription.cancelled":
        from product_features import set_premium_status
        if expires_at and expires_at > datetime.utcnow():
            set_premium_status(int(user_id), True, expires_at, entity.get("status"))
            mark_subscription_cancellation_requested(int(user_id), True)
        else:
            set_premium_status(int(user_id), False, expires_at, entity.get("status"))
    elif event in terminal_events:
        from product_features import set_premium_status
        set_premium_status(int(user_id), False, expires_at, entity.get("status"))
    return jsonify({"ok": True})


@app.route("/privacy")
def privacy_policy():
    return render_template("privacy.html")

@app.route("/terms")
def terms_of_service():
    return render_template("terms.html")

@app.route("/financial-disclaimer")
def financial_disclaimer():
    return render_template("financial_disclaimer.html")

@app.route("/support")
def support_page():
    return render_template("support.html")

@app.route("/intelligence", methods=["GET", "POST"])
def intelligence():
    user = get_current_user()
    if not user:
        return redirect("/login")
    status = get_premium_status(user["id"])
    context = get_ai_financial_context(user["id"])
    month, year = datetime.now().month, datetime.now().year
    budgets_data = get_budgets(user["id"], month, year)
    for b in budgets_data:
        b["spent"] = get_budget_spending(user["id"], b["category"], month, year)
    goals_data = get_goals(user["id"])
    result = build_intelligence(context, budgets_data, goals_data)
    simulation = None
    what_if_question = ""
    what_if_followup = None
    if request.method == "POST":
        if not status["is_premium"]:
            return redirect("/premium")
        what_if_question = request.form.get("what_if_question", "").strip()
        supplied_amount = request.form.get("what_if_amount", "").strip()
        parsed = run_limited_ai(user["id"], parse_what_if_question, what_if_question, _sigora_language())
        if isinstance(parsed, str):
            what_if_followup = parsed
        else:
            amount = parsed.get("amount")
            if supplied_amount:
                try:
                    amount = float(supplied_amount)
                except ValueError:
                    amount = None
            if not amount:
                what_if_followup = "price"
            else:
                simulation = simulate_purchase(context, amount, goals_data, parsed.get("subject"), parsed.get("timeframe"))
    return render_template("intelligence.html", intelligence=result, simulation=simulation, is_premium=status["is_premium"], what_if_question=what_if_question, what_if_followup=what_if_followup)

@app.route("/premium")
def premium():
    user = get_current_user()
    if not user:
        return redirect("/login")
    settings_data = get_user_settings(user["id"])
    status = get_premium_status(user["id"])
    usage = get_ai_usage(user["id"])
    ai_limits = get_ai_limits(status["is_premium"])
    pricing = get_pricing(user.get("currency", "INR"), user.get("country", "India"))
    context = get_ai_financial_context(user["id"])
    month, year = datetime.now().month, datetime.now().year
    intel_budgets = get_budgets(user["id"], month, year)
    for b in intel_budgets:
        b["spent"] = get_budget_spending(user["id"], b["category"], month, year)
    intelligence = build_intelligence(context, intel_budgets, get_goals(user["id"]))
    payment_ready = bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET") and pricing.get("plan_id"))
    return render_template("premium.html", settings=settings_data, premium_features=premium_features(intelligence), premium_status=status, ai_usage=usage, ai_limits=ai_limits, payment_ready=payment_ready, pricing=pricing, intelligence=intelligence)

def _admin_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.remote_addr) or "unknown"


def _admin_csrf_token():
    token = session.get("admin_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["admin_csrf_token"] = token
    return token


def _verify_admin_csrf():
    supplied = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("admin_csrf_token", "")
    return bool(expected and supplied and hmac.compare_digest(expected, supplied))


def _current_admin():
    admin_id = session.get("admin_user_id")
    if not admin_id:
        return None
    identity = get_admin_identity(admin_id)
    if not identity or identity.get("role") not in {"super_admin", "admin", "support"} or identity.get("account_status") != "active":
        session.pop("admin_user_id", None)
        return None
    return identity


def admin_required(roles=("super_admin", "admin")):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            admin = _current_admin()
            if not admin:
                return redirect("/admin/login?next=" + request.path)
            if admin.get("role") not in roles:
                return "Forbidden", 403
            if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not _verify_admin_csrf():
                audit(admin["id"], "csrf_rejected", details=request.path, ip_address=_admin_ip())
                return "Invalid or expired form token. Refresh the page and try again.", 400
            return fn(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_admin_globals():
    return {"admin_identity": _current_admin(), "admin_csrf_token": _admin_csrf_token() if session.get("admin_user_id") else ""}


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if _current_admin():
        return redirect("/admin")
    error = None
    login_csrf = _admin_csrf_token()
    if request.method == "POST":
        if not _verify_admin_csrf():
            return render_template("admin_login.html", error="Invalid or expired form token.", login_csrf=login_csrf), 400
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        ip = _admin_ip()
        if admin_login_blocked(email, ip):
            return render_template("admin_login.html", error="Too many failed attempts. Try again later."), 429
        user = get_user_by_email(email) if email else None
        identity = get_admin_identity(user["id"]) if user else None
        valid = bool(user and identity and identity.get("role") in {"super_admin", "admin", "support"}
                     and identity.get("account_status") == "active" and check_user_password(password, user["password_hash"]))
        record_admin_login(email, ip, valid)
        if not valid:
            return render_template("admin_login.html", error="Invalid admin credentials."), 401
        session.pop("user_id", None)
        session["admin_user_id"] = user["id"]
        session["admin_last_seen"] = datetime.utcnow().isoformat()
        session["admin_csrf_token"] = secrets.token_urlsafe(32)
        touch_last_login(user["id"])
        audit(user["id"], "admin_login", details="Admin session started", ip_address=ip)
        next_path = request.args.get("next", "")
        return redirect(next_path if next_path.startswith("/admin") and not next_path.startswith("//") else "/admin")
    return render_template("admin_login.html", error=error, expired=request.args.get("expired"), login_csrf=login_csrf)


@app.route("/admin/logout", methods=["POST"])
@admin_required(roles=("super_admin", "admin", "support"))
def admin_logout():
    admin = _current_admin()
    if admin:
        audit(admin["id"], "admin_logout", details="Admin session ended", ip_address=_admin_ip())
    session.pop("admin_user_id", None)
    session.pop("admin_last_seen", None)
    session.pop("admin_csrf_token", None)
    return redirect("/admin/login")


@app.route("/admin")
@admin_required(roles=("super_admin", "admin", "support"))
def admin_dashboard():
    return render_template("admin_dashboard.html", metrics=dashboard_metrics(), activity=recent_activity(15))


@app.route("/admin/users")
@admin_required(roles=("super_admin", "admin", "support"))
def admin_users():
    search=request.args.get("q","").strip(); status=request.args.get("status","").strip(); plan=request.args.get("plan","").strip()
    return render_template("admin_users.html", users=admin_list_users(search,status,plan), search=search, status=status, plan=plan)


@app.route("/admin/users/<int:user_id>")
@admin_required(roles=("super_admin", "admin", "support"))
def admin_user(user_id):
    user=admin_user_detail(user_id)
    if not user: return "Not found",404
    return render_template("admin_user.html", user=user)


@app.route("/admin/users/<int:user_id>/status", methods=["POST"])
@admin_required()
def admin_user_status(user_id):
    admin=_current_admin(); status=request.form.get("status",""); reason=request.form.get("reason","").strip() or None
    set_account_status(user_id,status,reason)
    audit(admin["id"],"account_status_changed",user_id,f"status={status}; reason={reason or ''}",_admin_ip())
    return redirect(f"/admin/users/{user_id}")


@app.route("/admin/users/<int:user_id>/premium", methods=["POST"])
@admin_required()
def admin_user_premium(user_id):
    admin=_current_admin(); active=request.form.get("active")=="1"
    set_user_premium(user_id,active)
    audit(admin["id"],"premium_granted" if active else "premium_revoked",user_id,"Manual admin change",_admin_ip())
    return redirect(f"/admin/users/{user_id}")


@app.route("/admin/users/<int:user_id>/note", methods=["POST"])
@admin_required(roles=("super_admin", "admin", "support"))
def admin_user_note(user_id):
    admin=_current_admin(); note=request.form.get("note","").strip()
    if note:
        add_admin_note(user_id,admin["id"],note)
        audit(admin["id"],"admin_note_added",user_id,note[:200],_admin_ip())
    return redirect(f"/admin/users/{user_id}")


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required(roles=("super_admin",))
def admin_user_delete(user_id):
    admin=_current_admin(); confirmation=request.form.get("confirm","").strip().upper()
    if confirmation != "DELETE":
        return redirect(f"/admin/users/{user_id}?delete_error=1")
    # Audit before cascade deletion; target_user_id becomes NULL if the user is deleted.
    audit(admin["id"],"user_deleted",user_id,"Permanent account deletion approved",_admin_ip())
    delete_managed_user(user_id)
    return redirect("/admin/users?deleted=1")



@app.route("/admin/staff", methods=["GET", "POST"])
@admin_required(roles=("super_admin",))
def admin_staff():
    admin = _current_admin()
    error = None
    changed = None
    if request.method == "POST":
        try:
            target_user_id = int(request.form.get("user_id", "0"))
            new_role = request.form.get("role", "user").strip()
            result = set_staff_role(target_user_id, new_role, admin["id"])
            audit(admin["id"], "staff_role_changed", target_user_id,
                  f"{result['old_role']}->{result['new_role']}; email={result['email']}", _admin_ip())
            changed = f"{result['email']} is now {result['new_role'].replace('_',' ')}."
        except Exception as exc:
            error = str(exc)
    q = request.args.get("q", "").strip()
    return render_template("admin_staff.html", staff=list_staff_accounts(),
                           candidates=search_staff_candidates(q), q=q,
                           staff_error=error, staff_changed=changed)


@app.route("/admin/coupons", methods=["GET","POST"])
@admin_required()
def admin_coupons():
    admin=_current_admin(); ensure_monetization_schema(); error=None
    if request.method=="POST":
        action=request.form.get("action")
        try:
            if action=="create":
                create_coupon(request.form.get("code",""),request.form.get("discount_type","percent"),float(request.form.get("discount_value","0")),int(request.form["max_uses"]) if request.form.get("max_uses") else None,request.form.get("valid_until") or None,request.form.get("first_month_only")=="on",request.form.get("razorpay_offer_id","").strip() or None)
                audit(admin["id"],"coupon_created",details=request.form.get("code","").upper(),ip_address=_admin_ip())
            elif action=="toggle":
                cid=int(request.form["coupon_id"]); active=request.form.get("active")=="1"; toggle_coupon(cid,active)
                audit(admin["id"],"coupon_toggled",details=f"coupon_id={cid}; active={active}",ip_address=_admin_ip())
        except Exception as exc:
            error=str(exc)
    return render_template("admin_coupons.html", coupons=list_coupons(), premium_price=get_pricing()["premium_price"], admin_error=error)


@app.route("/admin/analytics")
@admin_required(roles=("super_admin", "admin", "support"))
def admin_analytics():
    return render_template("admin_analytics.html", analytics=feature_analytics(), metrics=dashboard_metrics())


@app.route("/admin/support")
@admin_required(roles=("super_admin", "admin", "support"))
def admin_support():
    return render_template("admin_support.html", messages=list_support_messages())


@app.route("/admin/announcements", methods=["GET","POST"])
@admin_required()
def admin_announcements():
    admin = _current_admin()
    sent = None
    updated = None
    error = None
    if request.method == "POST":
        action = request.form.get("action", "create")
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        link = request.form.get("link", "").strip() or None
        try:
            if not title or not message:
                raise ValueError("Title and message are required.")
            translations = {
                "ta": translate_announcement_text(title, message, "ta"),
                "hi": translate_announcement_text(title, message, "hi"),
            }
            if action == "update":
                announcement_id = int(request.form.get("announcement_id", "0"))
                affected = update_announcement(announcement_id, title, message, link, translations=translations)
                updated = announcement_id
                audit(admin["id"], "announcement_edited", details=f"announcement_id={announcement_id}; recipient_copies={affected}; title={title}; localized=ta,hi", ip_address=_admin_ip())
            else:
                audience = request.form.get("audience", "all")
                sent = create_announcement(admin["id"], title, message, link, audience, translations=translations)
                audit(admin["id"], "announcement_sent", details=f"audience={audience}; recipients={sent}; title={title}; localized=ta,hi", ip_address=_admin_ip())
        except Exception as exc:
            error = str(exc)
    edit_id = request.args.get("edit", "").strip()
    edit_announcement = None
    if edit_id.isdigit():
        edit_announcement = get_announcement(int(edit_id))
    return render_template("admin_announcements.html", announcements=list_announcements(), sent=sent,
                           updated=updated, admin_error=error, edit_announcement=edit_announcement)


@app.route("/admin/announcements/<int:announcement_id>/delete", methods=["POST"])
@admin_required(roles=("super_admin",))
def admin_announcement_delete(announcement_id):
    admin = _current_admin()
    result = delete_announcement(announcement_id)
    if result:
        audit(admin["id"], "announcement_deleted", details=f"announcement_id={announcement_id}; removed_recipient_copies={result['removed_alerts']}; title={result['title']}", ip_address=_admin_ip())
        return redirect(f"/admin/announcements?deleted={result['removed_alerts']}")
    return redirect("/admin/announcements?delete_missing=1")


@app.route("/admin/payments")
@admin_required(roles=("super_admin", "admin"))
def admin_payments():
    return render_template("admin_payments.html", payments=list_payment_events())


@app.route("/admin/audit")
@admin_required(roles=("super_admin", "admin"))
def admin_audit():
    return render_template("admin_audit.html", activity=recent_activity(200))


@app.route("/admin/system")
@admin_required(roles=("super_admin", "admin"))
def admin_system():
    return render_template("admin_system.html", health=system_health())


def get_current_user():
    ensure_feature_schema()
    ensure_admin_schema()
    user_id = session.get("user_id")

    if not user_id:
        return None

    access = get_user_access_state(user_id)
    if not access or access.get("account_status") != "active":
        session.pop("user_id", None)
        return None
    return get_user_by_id(user_id)

def categorize_transaction(description, transaction_type):
    """
    Automatically categorizes a transaction
    based on its description.
    """

    description = description.lower().strip()

    # -----------------------------
    # INCOME CATEGORIES
    # -----------------------------

    if transaction_type == "income":

        if any(word in description for word in [
            "salary",
            "payroll",
            "salary credit"
        ]):
            return "Salary"

        if any(word in description for word in [
            "freelance",
            "freelancer",
            "consulting",
            "consultation"
        ]):
            return "Freelance"

        if any(word in description for word in [
            "interest",
            "bank interest"
        ]):
            return "Interest"

        if any(word in description for word in [
            "refund",
            "cashback",
            "cash back"
        ]):
            return "Refund"

        return "Other Income"


    # -----------------------------
    # EXPENSE CATEGORIES
    # -----------------------------

    if transaction_type == "expense":

        # Food
        if any(word in description for word in [
            "swiggy",
            "zomato",
            "dominos",
            "pizza",
            "mcdonald",
            "kfc",
            "restaurant",
            "cafe",
            "food"
        ]):
            return "Food"

        # Shopping
        if any(word in description for word in [
            "amazon",
            "flipkart",
            "myntra",
            "ajio",
            "shopping",
            "mall",
            "retail"
        ]):
            return "Shopping"

        # Transport
        if any(word in description for word in [
            "uber",
            "ola",
            "rapido",
            "metro",
            "bus",
            "train",
            "transport"
        ]):
            return "Transport"

        # Fuel
        if any(word in description for word in [
            "petrol",
            "fuel",
            "diesel",
            "hpcl",
            "bpcl",
            "iocl"
        ]):
            return "Fuel"

        # Entertainment
        if any(word in description for word in [
            "netflix",
            "spotify",
            "prime video",
            "hotstar",
            "youtube",
            "movie",
            "cinema",
            "entertainment"
        ]):
            return "Entertainment"

        # Utilities
        if any(word in description for word in [
            "electricity",
            "eb bill",
            "water bill",
            "gas bill",
            "broadband",
            "internet",
            "wifi",
            "mobile recharge",
            "recharge"
        ]):
            return "Utilities"

        # Housing
        if any(word in description for word in [
            "rent",
            "maintenance",
            "housing",
            "apartment"
        ]):
            return "Housing"

        # Healthcare
        if any(word in description for word in [
            "hospital",
            "doctor",
            "pharmacy",
            "medical",
            "medicine",
            "apollo",
            "healthcare"
        ]):
            return "Healthcare"

        # Insurance
        if any(word in description for word in [
            "insurance",
            "lic premium",
            "policy premium"
        ]):
            return "Insurance"

        # Education
        if any(word in description for word in [
            "college",
            "school",
            "tuition",
            "course",
            "udemy",
            "coursera",
            "education"
        ]):
            return "Education"

        # Travel
        if any(word in description for word in [
            "flight",
            "airline",
            "hotel",
            "booking",
            "travel",
            "airbnb"
        ]):
            return "Travel"

        return "Uncategorized"

    return "Uncategorized"

@app.route("/import-transactions", methods=["GET", "POST"])
def import_transactions():
    user = get_current_user()
    if not user:
        return redirect("/login")
    if request.method == "GET":
        return render_template("import_transactions.html", accounts=list_financial_accounts(user["id"]), selected_account_id=request.args.get("account_id"))

    file = request.files.get("file")
    if not file or not file.filename:
        return render_template("import_transactions.html", error="Please select a statement file.")

    max_mb = int(os.getenv("IMPORT_MAX_FILE_MB", "25"))
    if request.content_length and request.content_length > max_mb * 1024 * 1024:
        return render_template("import_transactions.html", error=f"That file is larger than the {max_mb} MB import limit.")

    account_id = request.form.get("account_id") or request.args.get("account_id")
    available_accounts = list_financial_accounts(user["id"])
    if request.method == "POST" and available_accounts and not account_id:
        return render_template("import_transactions.html", error=_t("choose_import_account"), accounts=available_accounts)
    account = None
    if account_id:
        try: account = get_financial_account(user["id"], int(account_id))
        except (TypeError, ValueError): account = None
        if not account:
            return render_template("import_transactions.html", error="Choose a valid account for this statement.", accounts=list_financial_accounts(user["id"]))
    password = request.form.get("pdf_password") or None
    try:
        rows, columns, detected_format = read_statement(file, file.filename, password=password)
        normalized, errors = normalize_rows(rows, columns, categorize_transaction)
        detected_balance = infer_statement_balance(rows, columns)
    except ValueError as exc:
        msg = str(exc)
        if msg == "PDF_PASSWORD_REQUIRED":
            return render_template("import_transactions.html", error="This PDF is password protected. Enter its PDF password to continue.", password_required=True)
        if msg == "PDF_PASSWORD_INVALID":
            return render_template("import_transactions.html", error="That PDF password is incorrect. Please try again.", password_required=True)
        return render_template("import_transactions.html", error=msg, password_required=detected_format if 'detected_format' in locals() else False)
    except Exception as exc:
        print("IMPORT ERROR:", repr(exc))
        return render_template("import_transactions.html", error="Sigora couldn't read that statement safely. Please check the file and try again.")

    # Remove duplicates inside the uploaded statement.
    unique, seen = [], set()
    for t in normalized:
        key=(t["date"], t["description"].strip().lower(), t["transaction_type"], round(float(t["amount"]),2))
        if key not in seen:
            seen.add(key); unique.append(t)
    normalized=unique

    candidates=[(t["date"],t["description"],t["transaction_type"],t["amount"]) for t in normalized]
    existing=find_existing_transaction_keys(user["id"], candidates)
    importable=[t for t in normalized if (t["date"],t["description"].strip().lower(),t["transaction_type"],round(float(t["amount"]),2)) not in existing]
    skipped=len(normalized)-len(importable)

    if request.form.get("confirm") == "1":
        if account:
            count = 0
            for t in importable:
                fingerprint = hashlib.sha256(f"{t['date']}|{t['description'].strip().lower()}|{t['transaction_type']}|{float(t['amount']):.2f}".encode("utf-8")).hexdigest()
                tx = dict(t, source="statement_import", currency=account.get("currency") or user.get("currency","INR"), external_id=fingerprint)
                if import_external_transaction(user["id"], tx, account["id"])["created"]:
                    count += 1
            touch_financial_account(user["id"], account["id"], detected_balance)
        else:
            count=batch_add_transactions(user["id"], [dict(t,source="import",currency=user.get("currency","INR")) for t in importable])
        if count:
            award_activity(user["id"], "transaction", min(50,count))
        return render_template("import_transactions.html", success=True, imported_count=count, skipped_count=skipped, error_count=len(errors), errors=errors, accounts=list_financial_accounts(user["id"]), selected_account_id=account_id)

    return render_template("import_transactions.html", preview=True, preview_rows=importable[:200], total_found=len(normalized), importable_count=len(importable), skipped_count=skipped, error_count=len(errors), errors=errors[:20], original_filename=file.filename, detected_format=detected_format, password_required=bool(detected_format == "pdf" and password), accounts=list_financial_accounts(user["id"]), selected_account_id=account_id, selected_account=account)





def _market_search(query):
    """Resolve a company/fund name or ticker using Yahoo Finance public search."""
    try:
        r=requests.get("https://query1.finance.yahoo.com/v1/finance/search", params={"q":query,"quotesCount":8,"newsCount":0}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
        r.raise_for_status()
        out=[]
        for q in r.json().get("quotes",[]):
            if q.get("symbol") and q.get("quoteType") in {"EQUITY","ETF","MUTUALFUND","INDEX"}:
                out.append({"symbol":q.get("symbol"),"name":q.get("longname") or q.get("shortname") or q.get("symbol"),"exchange":q.get("exchDisp") or q.get("exchange") or "", "type":q.get("quoteType","")})
        return out
    except Exception:
        return []

def _market_symbol_candidates(symbol, holding_currency="", name=""):
    """Return sensible Yahoo ticker candidates without requiring users to know exchange suffixes."""
    raw=(symbol or "").strip().upper()
    cur=(holding_currency or "").strip().upper()
    candidates=[]
    def add(v):
        v=(v or "").strip().upper()
        if v and v not in candidates:
            candidates.append(v)
    known_suffixes=(".NS",".BO",".L",".TO",".AX",".HK",".SI",".PA",".DE",".F",".SA")
    if raw:
        if raw.endswith(known_suffixes) or raw.startswith("^") or "=" in raw or "-" in raw:
            add(raw)
        elif cur == "INR":
            add(raw+".NS"); add(raw+".BO"); add(raw)
        else:
            add(raw); add(raw+".NS"); add(raw+".BO")
    # Name search helps recover from incomplete/wrong raw tickers and works for funds/indices too.
    if name:
        try:
            for hit in _market_search(name)[:6]:
                hs=hit.get("symbol")
                if cur == "INR":
                    # Prefer Indian listings for INR holdings when Yahoo returns several global matches.
                    if str(hs or "").upper().endswith((".NS",".BO")):
                        add(hs)
                else:
                    add(hs)
            if cur == "INR":
                for hit in _market_search(name)[:6]:
                    add(hit.get("symbol"))
        except Exception:
            pass
    return candidates[:8]

def _resolve_market_quote(symbol, name="", holding_currency=""):
    """Resolve a user-friendly ticker then fetch and validate the latest supported market quote."""
    for candidate in _market_symbol_candidates(symbol, holding_currency, name):
        m=_market_chart(candidate,"5d","1d")
        if not m:
            continue
        try:
            price=float(m.get("price"))
        except (TypeError,ValueError):
            continue
        if not math.isfinite(price) or price <= 0:
            continue
        m["requested_symbol"]=(symbol or "").strip().upper()
        m["resolved_symbol"]=candidate
        m["source"]="Yahoo Finance"
        m["fetched_at"]=datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
        return m
    return None

def _market_chart(symbol, range_="1mo", interval="1d"):
    """Fetch market metadata plus a real historical series; never fabricate chart points."""
    try:
        def fetch_chart(fetch_symbol):
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{fetch_symbol}",
                params={"range": range_, "interval": interval},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=6,
            )
            r.raise_for_status()
            result = (r.json().get("chart", {}).get("result") or [None])[0]
            if not result:
                return None, []
            ts = result.get("timestamp", [])
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            closes = quote.get("close", [])
            points = [{"t": t, "v": v} for t, v in zip(ts, closes) if v is not None]
            return result, points

        result, points = fetch_chart(symbol)
        if not result:
            return None
        meta = result.get("meta", {})

        # A two-point multi-month chart is misleading: Chart.js renders it as a
        # perfect diagonal. BSE history can be sparse on Yahoo, so use the same
        # company's NSE listing for HISTORY only when the BSE series is sparse.
        min_points = {"5d": 3, "1mo": 5, "6mo": 20, "1y": 30, "5y": 30}.get(range_, 3)
        if len(points) < min_points and symbol.upper().endswith(".BO"):
            fallback_symbol = symbol[:-3] + ".NS"
            try:
                _, fallback_points = fetch_chart(fallback_symbol)
                if len(fallback_points) >= min_points:
                    points = fallback_points
            except Exception:
                pass

        # Do not draw a fake-looking straight trend from only one/two sparse
        # observations. The UI will clearly report unavailable history instead.
        if len(points) < 3:
            points = []

        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        change = (price - prev) if price is not None and prev else None
        pct = (change / prev * 100) if change is not None and prev else None
        return {
            "symbol": symbol, "name": meta.get("longName") or meta.get("shortName") or symbol,
            "exchange": meta.get("exchangeName") or meta.get("fullExchangeName") or "",
            "currency": meta.get("currency") or "", "price": price, "previous_close": prev,
            "change": change, "change_pct": pct, "day_high": meta.get("regularMarketDayHigh"),
            "day_low": meta.get("regularMarketDayLow"), "fifty_two_high": meta.get("fiftyTwoWeekHigh"),
            "fifty_two_low": meta.get("fiftyTwoWeekLow"), "points": points,
        }
    except Exception:
        return None

def _plain_market_explanation(m):
    if not m or m.get("price") is None: return "Live market data is temporarily unavailable. Try again shortly."
    pct=m.get("change_pct")
    if pct is None: tone="The latest price is available, but today's comparison is unavailable."
    elif pct >= 2: tone=f"The price is up {pct:.2f}% today — a noticeable positive move for one session."
    elif pct > 0: tone=f"The price is up {pct:.2f}% today — a modest positive move."
    elif pct <= -2: tone=f"The price is down {abs(pct):.2f}% today — a noticeable decline for one session."
    elif pct < 0: tone=f"The price is down {abs(pct):.2f}% today — a modest decline."
    else: tone="The price is roughly unchanged today."
    pts=m.get("points") or []
    if len(pts)>1 and pts[0]["v"]:
        period=(pts[-1]["v"]/pts[0]["v"]-1)*100
        trend=f" Over the displayed period it has {'risen' if period>=0 else 'fallen'} about {abs(period):.1f}%."
    else: trend=""
    return tone+trend+" Short-term price moves do not tell you whether an investment is suitable; look at the business/fund, diversification, time horizon and risk as well."

def _refresh_holding_market_prices(user_id, holdings, force=False, max_refresh=12):
    """Refresh supported holdings without turning a large portfolio into a slow serial page load."""
    now=datetime.utcnow(); candidates=[]
    for h in holdings:
        if not h.get("symbol"):
            continue
        stale=True
        stamp=h.get("market_price_updated_at")
        if stamp and not force:
            try:
                stale=(now-datetime.fromisoformat(stamp)).total_seconds() >= 900
            except Exception:
                stale=True
        if stale:
            candidates.append(h)
        if len(candidates) >= max_refresh:
            break
    if not candidates:
        return 0,0
    ok=0
    def fetch(h):
        return h, _resolve_market_quote(h.get("symbol"), h.get("name",""), h.get("currency",""))
    with ThreadPoolExecutor(max_workers=min(6,len(candidates))) as pool:
        futures=[pool.submit(fetch,h) for h in candidates]
        for fut in as_completed(futures):
            try:
                h,m=fut.result()
                if m and m.get("price") is not None:
                    price=float(m["price"])
                    market_currency=(m.get("currency") or h.get("currency") or "INR").upper()
                    holding_currency=(h.get("currency") or market_currency).upper()
                    if market_currency != holding_currency:
                        price=float(convert_amount(price,market_currency,holding_currency,datetime.now().strftime("%Y-%m-%d")))
                    update_investment_price(user_id,h["id"],price,m.get("change_pct"),market_sync=True,resolved_symbol=m.get("resolved_symbol"))
                    ok+=1
            except Exception:
                pass
    return ok,len(candidates)


def _portfolio_life_context(user, portfolio, profile):
    cash=0.0; liabilities=0.0; base_currency=user.get("currency","INR")
    try:
        for a in list_financial_accounts(user["id"]):
            bal=a.get("live_balance")
            if bal is None: continue
            amount=float(bal or 0); cur=a.get("currency") or base_currency
            if cur != base_currency:
                try: amount=float(convert_amount(amount,cur,base_currency,datetime.now().strftime("%Y-%m-%d")))
                except Exception: continue
            if str(a.get("account_type") or "").lower() in {"credit_card","loan","liability","bnpl"}: liabilities += max(0,amount)
            else: cash += amount
    except Exception:
        pass
    investments=float(portfolio.get("value") or 0)
    net_worth=cash+investments-liabilities
    invested_share=(investments/net_worth*100) if net_worth>0 else None
    return {"cash":cash,"liabilities":liabilities,"investments":investments,"net_worth":net_worth,
            "invested_share":invested_share,"down20":investments*0.20,
            "largest":portfolio.get("biggest_holding"),"largest_pct":portfolio.get("biggest_pct",0),
            "emergency_months":float((profile or {}).get("emergency_months",0) or 0)}


def _investment_goal_connections(user, portfolio):
    out=[]
    base=user.get("currency","INR"); pvalue=float(portfolio.get("value") or 0)
    for g in get_goals(user["id"]):
        target=float(g.get("target_amount") or 0); saved=float(g.get("current_amount") or 0); cur=g.get("currency") or base
        target_base=target; saved_base=saved
        if cur != base:
            try:
                target_base=float(convert_amount(target,cur,base,datetime.now().strftime("%Y-%m-%d"))); saved_base=float(convert_amount(saved,cur,base,datetime.now().strftime("%Y-%m-%d")))
            except Exception:
                continue
        pct=(pvalue/target_base*100) if target_base>0 else 0
        out.append({**g,"target_base":target_base,"saved_base":saved_base,"portfolio_pct":pct})
    return out[:5]


def _localized_investment_messages(cashflow, portfolio):
    cash=[]
    for msg in cashflow.get("messages", []):
        if msg.startswith("Your tracked expenses currently meet or exceed"):
            cash.append(_t("warn_cashflow"))
        elif msg.startswith("Your chosen monthly investment amount is higher"):
            cash.append(_t("warn_monthly_gt_surplus"))
        elif msg.startswith("Your entered emergency-fund coverage is below"):
            cash.append(_t("warn_emergency_low"))
        else:
            cash.append(msg)
    warnings=[]
    import re
    for msg in portfolio.get("warnings", []):
        m=re.match(r"([0-9.]+)% of your tracked portfolio is in (.+)\. High concentration", msg)
        if m:
            _asset_labels={"Stock":_t("asset_stock"),"Index fund / ETF":_t("asset_index_etf"),"Mutual fund":_t("asset_mutual_fund"),"Fixed income":_t("asset_fixed_income"),"Gold":_t("asset_gold"),"Cash / liquid":_t("asset_cash_liquid"),"Other":_t("asset_other")}
            warnings.append(_t("warn_asset_concentration").format(pct=m.group(1), name=_asset_labels.get(m.group(2),m.group(2)))); continue
        m=re.match(r"([0-9.]+)% of your tracked portfolio is in the (.+) sector\.", msg)
        if m:
            warnings.append(_t("warn_sector_concentration").format(pct=m.group(1), name=m.group(2))); continue
        m=re.match(r"(.+) is ([0-9.]+)% of the tracked portfolio\.", msg)
        if m:
            warnings.append(_t("warn_holding_concentration").format(name=m.group(1), pct=m.group(2))); continue
        warnings.append(msg)
    return cash, warnings

@app.route("/invest")
def invest():
    user=get_current_user()
    if not user: return redirect("/login")
    profile=get_profile(user["id"])
    initial=portfolio_summary(user["id"])
    _refresh_holding_market_prices(user["id"], initial.get("holdings",[]), force=False, max_refresh=12)
    portfolio=portfolio_summary(user["id"])
    cashflow=financial_investment_context(user["id"], profile)
    cashflow_messages, portfolio_warning_texts = _localized_investment_messages(cashflow, portfolio)
    health=portfolio_health(portfolio,cashflow)
    life=_portfolio_life_context(user,portfolio,profile)
    goal_connections=_investment_goal_connections(user,portfolio)
    allocation=model_allocation(profile["profile"]) if profile else None
    watchlist=get_watchlist(user["id"])
    for item in watchlist:
        item["market"]=_market_chart(item.get("symbol"), "5d", "1d") if item.get("symbol") else None
    return render_template("invest.html", profile=profile, portfolio=portfolio, cashflow=cashflow, cashflow_messages=cashflow_messages, portfolio_warning_texts=portfolio_warning_texts, health=health, life=life, goal_connections=goal_connections, allocation=allocation, watchlist=watchlist, explorer=EXPLORER)

@app.route("/invest/refresh-prices", methods=["POST"])
def investment_refresh_prices():
    user=get_current_user()
    if not user: return redirect("/login")
    holdings=portfolio_summary(user["id"]).get("holdings",[])
    ok,total=_refresh_holding_market_prices(user["id"],holdings,force=True,max_refresh=36)
    flash(_t("prices_refreshed") if ok==total else _t("price_refresh_partial"), "success" if ok else "warning")
    return redirect("/invest")

@app.route("/invest/profile", methods=["GET","POST"])
def investment_profile():
    user=get_current_user()
    if not user: return redirect("/login")
    if request.method == "POST":
        try:
            save_profile(user["id"], request.form.get("objective","growth"), int(request.form.get("horizon_years",5)), request.form.get("risk_comfort","moderate"), request.form.get("loss_reaction","hold"), float(request.form.get("emergency_months",0) or 0), float(request.form.get("monthly_investment",0) or 0))
            flash("Investor profile updated.", "success")
            return redirect("/invest")
        except ValueError:
            flash("Please enter valid numbers.", "danger")
    return render_template("investment_profile.html", profile=get_profile(user["id"]))

@app.route("/invest/holding/add", methods=["POST"])
def investment_add():
    user=get_current_user()
    if not user: return redirect("/login")
    try:
        name=request.form.get("name","").strip()
        symbol=request.form.get("symbol","").strip().upper()
        market=_resolve_market_quote(symbol,name,user.get("currency","INR")) if (symbol or name) else None
        if market and market.get("resolved_symbol"):
            symbol=market["resolved_symbol"]
        manual=request.form.get("current_price","").strip()
        if market and market.get("price") is not None:
            current=float(market["price"])
            market_currency=(market.get("currency") or user.get("currency","INR")).upper()
            user_currency=user.get("currency","INR").upper()
            if market_currency != user_currency:
                current=float(convert_amount(current,market_currency,user_currency,datetime.now().strftime("%Y-%m-%d")))
        elif manual:
            current=float(manual)
        else:
            flash(_t("market_price_missing"),"warning")
            return redirect("/invest")
        add_investment(user["id"], name, symbol, request.form.get("asset_type","Stock"), request.form.get("sector","").strip(), float(request.form.get("quantity",0)), float(request.form.get("average_cost",0)), current, user.get("currency","INR"), request.form.get("notes","").strip())
        # Persist market metadata on the newly inserted holding during the normal page refresh.
        flash("Investment added to your tracker.", "success")
    except (ValueError, TypeError): flash("Please enter valid investment values.", "danger")
    return redirect("/invest")

@app.route("/invest/holding/<int:investment_id>/price", methods=["POST"])
def investment_price(investment_id):
    user=get_current_user()
    if not user: return redirect("/login")
    try: update_investment_price(user["id"], investment_id, float(request.form.get("current_price",0)))
    except ValueError: flash("Please enter a valid price.", "danger")
    return redirect("/invest")

@app.route("/invest/holding/<int:investment_id>/delete", methods=["POST"])
def investment_delete(investment_id):
    user=get_current_user()
    if not user: return redirect("/login")
    delete_investment(user["id"], investment_id); flash("Investment removed.", "success")
    return redirect("/invest")

@app.route("/invest/watchlist/add", methods=["POST"])
def investment_watchlist_add():
    user=get_current_user()
    if not user: return redirect("/login")
    query=request.form.get("name","").strip()
    if query:
        matches=_market_search(query)
        chosen=matches[0] if matches else None
        if chosen:
            add_watchlist(user["id"], chosen["name"], chosen["symbol"], chosen.get("type") or "Stock", request.form.get("note","").strip())
            flash(f"{chosen['name']} added to your watchlist.", "success")
        else:
            flash("We couldn't find that investment. Try the company name or ticker (for example Reliance, AAPL or MSFT).", "danger")
    return redirect("/invest")

@app.route("/invest/watchlist/<int:item_id>/delete", methods=["POST"])
def investment_watchlist_delete(item_id):
    user=get_current_user()
    if not user: return redirect("/login")
    delete_watchlist(user["id"],item_id); return redirect("/invest")

@app.route("/invest/ai", methods=["POST"])
def investment_ai():
    user=get_current_user()
    if not user: return redirect("/login")
    profile=get_profile(user["id"]); portfolio=portfolio_summary(user["id"]); cashflow=financial_investment_context(user["id"],profile)
    context={"profile":profile,"portfolio":portfolio,"cashflow":cashflow,"model_allocation":model_allocation(profile["profile"]) if profile else None}
    ai_result=run_limited_ai(user["id"], get_investment_ai_insight, context)
    return render_template("investment_ai.html", ai_result=ai_result, profile=profile, portfolio=portfolio)


@app.route("/invest/market/<path:symbol>")
def investment_market_detail(symbol):
    user=get_current_user()
    if not user: return redirect("/login")
    period=request.args.get("period","1mo")
    allowed={"5d":("5d","30m"),"1mo":("1mo","1d"),"6mo":("6mo","1d"),"1y":("1y","1d"),"5y":("5y","1wk")}
    rng,interval=allowed.get(period,allowed["1mo"])
    market=_market_chart(symbol,rng,interval)
    explanation=_plain_market_explanation(market)
    return render_template("investment_market.html", market=market, symbol=symbol, period=period, explanation=explanation)

@app.route("/insights")
def insights():
    user = get_current_user()
    if not user:
        return redirect("/login")
    context = get_ai_financial_context(user["id"])
    ai_result = run_limited_ai(user["id"], get_ai_insights, context)
    status = get_premium_status(user["id"])
    usage = get_ai_usage(user["id"])
    ai_limits = get_ai_limits(status["is_premium"])
    return render_template("insights.html", ai_result=ai_result, is_premium=status["is_premium"], usage=usage, monthly_limit=ai_limits["monthly"], daily_limit=ai_limits["daily"])

@app.errorhandler(413)
def request_too_large(error):
    return render_template("import_transactions.html", error=f"That upload is too large. The maximum statement size is {os.getenv('IMPORT_MAX_FILE_MB', '25')} MB."), 413

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug)
