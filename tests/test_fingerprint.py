from src.analyzer.fingerprint import detect_platform

SHOPIFY_HTML = '<script src="https://cdn.shopify.com/s/files/1/theme.js"></script>'
WOOCOMMERCE_HTML = '<link rel="stylesheet" href="/wp-content/plugins/woocommerce/assets/css/woocommerce.css">'
PRESTASHOP_HTML = '<script>var prestashop = {};</script>'
MAGENTO_HTML = '<script type="text/x-magento-init">{"*":{"mage/cookies":{}}}</script>'
SQUARESPACE_HTML = '<link href="https://static.squarespace.com/universal/styles.css">'
WIX_HTML = '<link href="https://static.wixstatic.com/frog/main.css">'
WEBFLOW_HTML = '<script src="https://uploads-ssl.webflow.com/main.js">'
GENERIC_STORE_HTML = '<button class="add-to-cart">Añadir al carrito</button>'
GENERIC_CHECKOUT_HTML = '<a href="/checkout">Checkout</a>'
PLAIN_HTML = '<html><body><p>Bienvenido a nuestra web corporativa</p></body></html>'
VELFIX_FOOTER_HTML = '<footer>TECNOLOGÍA <a href="https://www.velfix.es">VELFIX</a></footer>'
VELFIX_MEIGASOFT_HTML = '<p>DESARROLLADO POR <a href="https://www.meigasoft.es">Meigasoft</a></p>'
VELFIX_VWEB_HTML = '<script>var vweb_web_configs = {"merchant": "frisee2"};</script>'


def test_detect_shopify():
    is_store, platform = detect_platform(SHOPIFY_HTML)
    assert is_store is True
    assert platform == "Shopify"


def test_detect_woocommerce():
    is_store, platform = detect_platform(WOOCOMMERCE_HTML)
    assert is_store is True
    assert platform == "WooCommerce"


def test_detect_prestashop():
    is_store, platform = detect_platform(PRESTASHOP_HTML)
    assert is_store is True
    assert platform == "PrestaShop"


def test_detect_magento():
    is_store, platform = detect_platform(MAGENTO_HTML)
    assert is_store is True
    assert platform == "Magento"


def test_detect_squarespace():
    is_store, platform = detect_platform(SQUARESPACE_HTML)
    assert is_store is True
    assert platform == "Squarespace"


def test_detect_wix():
    is_store, platform = detect_platform(WIX_HTML)
    assert is_store is True
    assert platform == "Wix"


def test_detect_webflow():
    is_store, platform = detect_platform(WEBFLOW_HTML)
    assert is_store is True
    assert platform == "Webflow"


def test_detect_generic_store_add_to_cart():
    is_store, platform = detect_platform(GENERIC_STORE_HTML)
    assert is_store is True
    assert platform == "Desconocida"


def test_detect_generic_store_checkout():
    is_store, platform = detect_platform(GENERIC_CHECKOUT_HTML)
    assert is_store is True
    assert platform == "Desconocida"


def test_not_a_store():
    is_store, platform = detect_platform(PLAIN_HTML)
    assert is_store is False
    assert platform is None


def test_detect_velfix_footer_link():
    is_store, platform = detect_platform(VELFIX_FOOTER_HTML)
    assert is_store is True
    assert platform == "Velfix"


def test_detect_velfix_meigasoft():
    is_store, platform = detect_platform(VELFIX_MEIGASOFT_HTML)
    assert is_store is True
    assert platform == "Velfix"


def test_detect_velfix_vweb_config():
    is_store, platform = detect_platform(VELFIX_VWEB_HTML)
    assert is_store is True
    assert platform == "Velfix"
