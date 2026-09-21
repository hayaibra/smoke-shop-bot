"""
اختبارات منطق الكتالوج والسلة — تشغيل: python -m unittest discover tests
ما بتحتاج توكن ولا شبكة إطلاقاً.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import catalog_logic as cl

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


class TestCatalogLoading(unittest.TestCase):
    def setUp(self):
        self.catalog = cl.load_catalog(CATALOG_PATH)

    def test_categories_order(self):
        self.assertEqual(
            cl.get_categories(self.catalog),
            ["دخان", "معسل", "فحم", "إكسسوارات", "اراكيل الكترونية", "قداحات"],
        )

    def test_category_button_label(self):
        self.assertEqual(cl.category_button_label(self.catalog, "دخان"), "🚬 دخان")
        self.assertEqual(cl.category_button_label(self.catalog, "معسل"), "💨 معسل")

    def test_types_of_section_are_real_brands(self):
        # الأنواع (types) هلق هيي براندات حقيقية من نشرة أسعار التاجر، مش بيانات تجريبية.
        self.assertIn("ماستر", cl.get_types(self.catalog, "دخان"))
        self.assertIn("اليغانس", cl.get_types(self.catalog, "دخان"))
        self.assertEqual(len(cl.get_types(self.catalog, "دخان")), 39)
        self.assertEqual(len(cl.get_types(self.catalog, "معسل")), 14)

    def test_dukhan_priority_brands_appear_first_in_requested_order(self):
        # التاجرة طلبت هالخمس ماركات تطلع أول شي بقائمة اختيار النوع (دخان)،
        # بنفس الترتيب يلي حددتو، وباقي الماركات بعدهن (بترتيبهن القديم).
        types = cl.get_types(self.catalog, "دخان")
        self.assertEqual(types[:5], ["ماستر", "كابتن بلاك", "كلواز 8 S", "البرو", "روز"])
        self.assertEqual(len(types), 39)  # ٤٠ ناقص "جتان" يلي انحذفت بالكامل بعدين

    def test_jitane_brand_fully_removed(self):
        # التاجرة حذفت ماركة "جتان" بالكامل (مو صنف واحد جواها — الماركة كلها)،
        # منشان ما تلتبس مع "جيتان" (ماركة تانية لحالها، لسا موجودة وما تأثرت).
        types = cl.get_types(self.catalog, "دخان")
        self.assertNotIn("جتان", types)
        self.assertIn("جيتان", types)
        self.assertEqual(cl.get_variants(self.catalog, "دخان", "جيتان"), ["جيتان قصير"])

    def test_ekhtimar_variants_after_cleanup(self):
        # التاجرة حذفت صنفين من "اختمار" (قصير، طويل — بلا أي وصف لون/نوع)،
        # نفس أسلوب باقي الحذوفات: محذوفين من الكتالوج بس، ولسا موجودين
        # بمكانهن تماماً بملف price_sheet.json.
        variants = cl.get_variants(self.catalog, "دخان", "اختمار")
        self.assertEqual(
            variants,
            ["اختمار قصير ازرق", "اختمار قصير فضي", "اختمار سليم فضي", "اختمار طويل ازرق"],
        )
        self.assertNotIn("اختمار قصير", variants)
        self.assertNotIn("اختمار طويل", variants)

    def test_oscar_variants_after_cleanup(self):
        # التاجرة حذفت ٣ أصناف من "اوسكار" (طويل، كوين، سليم — بلا وصف لون)،
        # وخلت بس الأصناف الموصوفة (طويل فضي، سليم فضي، كوين ازرق).
        variants = cl.get_variants(self.catalog, "دخان", "اوسكار")
        self.assertEqual(variants, ["اوسكار طويل فضي", "اوسكار سليم فضي", "اوسكار كوين ازرق"])
        self.assertNotIn("اوسكار طويل", variants)
        self.assertNotIn("اوسكار كوين", variants)
        self.assertNotIn("اوسكار سليم", variants)

    def test_elegance_variants_after_cleanup(self):
        # التاجرة حذفت ٤ أصناف من "اليغانس" (اسود كرتون، كوين بلا وصف، طويل
        # فضي غ م، سليم مربع) — بلا ما تأثر باقي أصنافها (٢١ صنف).
        variants = cl.get_variants(self.catalog, "دخان", "اليغانس")
        self.assertEqual(len(variants), 21)
        self.assertNotIn("اليغانس اسود كرتون", variants)
        self.assertNotIn("اليغانس كوين", variants)
        self.assertNotIn("اليغانس طويل فضي غ م", variants)
        self.assertNotIn("اليغانس سليم مربع", variants)
        # صنف تاني بنفس الاسم الجزئي ("طويل فضي غ" بلا "م") ما لازم يتأثر.
        self.assertIn("اليغانس طويل فضي غ", variants)

    def test_oris_variants_after_cleanup_and_rename(self):
        # التاجرة حذفت ٤ أصناف من "اوريس" (سليم، كوين، طقتين، قصير بطيخ —
        # كلهن بلا وصف إضافي)، وبدّلت اسم "اوريس طقة منغا غ" لـ"اوريس سليم
        # طقة منغا" (تبديل اسم بمكانه، مش حذف/إضافة).
        variants = cl.get_variants(self.catalog, "دخان", "اوريس")
        self.assertEqual(len(variants), 13)
        self.assertNotIn("اوريس سليم", variants)
        self.assertNotIn("اوريس كوين", variants)
        self.assertNotIn("اوريس طقتين", variants)
        self.assertNotIn("اوريس قصير بطيخ", variants)
        self.assertNotIn("اوريس طقة منغا غ", variants)
        self.assertIn("اوريس سليم طقة منغا", variants)
        # صنف تاني بنفس الاسم الجزئي ("سليم طقة توت") ما لازم يتأثر.
        self.assertIn("اوريس سليم طقة توت", variants)

    def test_napoli_variants_after_cleanup(self):
        # التاجرة حذفت 3 أصناف مكررة/زايدة من "نابولي" (قصير ابيض، قصير بس،
        # احمر + فضي قصير) وبدّلت اسم "قصير سلفر" لـ"قصير فضي" بتنضيف سابق،
        # وبعدين حذفت "نابولي قصير سفر" نهائياً كمان (بقيت دهبي/فضي/احمر بس).
        # ⚠️ "نابولي قصير سفر" محذوف من الكتالوج (ما عاد يظهر/ينختار بالبوت)،
        # بس لسا موجود لحاله بملف price_sheet.json (بلا حذف السطر) منشان رقم
        # (index) باقي الأصناف بعده ما يتحرك ويخرب أسعار محفوظة سابقاً — شوف
        # TestRealCatalogAndPriceSheetConsistency بـ test_cart_pricing.py.
        variants = cl.get_variants(self.catalog, "دخان", "نابولي")
        self.assertEqual(variants, ["نابولي قصير دهبي", "نابولي قصير فضي", "نابولي قصير احمر"])
        self.assertNotIn("نابولي قصير سلفر", variants)
        self.assertNotIn("نابولي قصير ابيض", variants)
        self.assertNotIn("نابولي قصير", variants)
        self.assertNotIn("نابولي احمر + فضي قصير", variants)
        self.assertNotIn("نابولي قصير سفر", variants)

    def test_winchester_variants_after_cleanup(self):
        # التاجرة حذفت ٤ أصناف زايدة/مكررة من "ون شيستر" — نفس أسلوب حذف
        # "نابولي قصير سفر" فوق: محذوفين من الكتالوج بس، ولسا موجودين بمكانهن
        # تماماً بملف price_sheet.json منشان ترقيم باقي الأصناف ما يتحرك.
        variants = cl.get_variants(self.catalog, "دخان", "ون شيستر")
        self.assertEqual(
            variants,
            [
                "ون شيستر كوين فضي",
                "ون شيستر كوين ازرق",
                "ون شيستر كوين دهبي",
                "ون شيستر سليم اسود",
                "ون شيستر سليم ازرق",
                "ون شيستر سليم فضي",
            ],
        )
        self.assertNotIn("ونشستر سليم", variants)
        self.assertNotIn("ونشستر كوين", variants)
        self.assertNotIn("ون شيستر كوين سيلفر", variants)
        self.assertNotIn("ون شيستر سليم ابيض دهبي", variants)

    def test_variants_present_match_real_items(self):
        variants = cl.get_variants(self.catalog, "دخان", "جيتان")
        self.assertIn("جيتان قصير", variants)
        self.assertEqual(len(variants), 1)

    def test_master_variants_replaced_with_simplified_lineup(self):
        # التاجرة استبدلت كامل تشكيلة "ماستر" (كانت ٢٣ صنف بأسماء/لواحق كتير
        # مربكة زي "م"، "طقتين دبل ...") بـ٧ أصناف بسيطة بس. ٦ من السبعة كانوا
        # موجودين أصلاً بنفس الاسم بالضبط (سعرهن القديم ضل زي ما هو)، وصنف
        # واحد بس جديد كلياً ("ماستر طويل" بلا أي وصف ورق/كرتون).
        variants = cl.get_variants(self.catalog, "دخان", "ماستر")
        self.assertEqual(
            variants,
            [
                "ماستر طويل",
                "ماستر قصير ازرق",
                "ماستر قصير فضي",
                "ماستر كوين ابيض",
                "ماستر كوين ازرق",
                "ماستر سليم فضي",
                "ماستر سليم ازرق",
            ],
        )
        for old in [
            "ماستر طويل ورق م", "ماستر قصير ازرق م", "ماستر كوين ابيض م", "ماستر سليم فضي م",
            "ماستر سليم بطيخ", "ماستر سليم بلوبيري", "ماستر سليم تفاح و نعنع",
            "ماستر سليم علكة ونعنع", "ماستر سليم نعنع مثلج", "ماستر طويل ورق", "ماستر طويل كرتون",
            "ماستر طقتين دبل ايس ميكس", "ماستر طقتين دبل سمر", "ماستر طقتين دبل فيوجين سمر",
            "ماستر طقتين دبل بلوسم فيوجين", "ماستر قصير فضي م", "ماستر سليم ازرق م",
        ]:
            self.assertNotIn(old, variants, msg=old)

    def test_tera_variants_after_cleanup_and_addition(self):
        # حذفنا صنف "تيرا بلو / سينا / اوسن بيرل حرة" (بقي بملف الأسعار كـ
        # orphan بنفس فهرسه الأصلي)، وأضفنا صنف جديد كلياً "تيرا تركواز".
        variants = cl.get_variants(self.catalog, "دخان", "تيرا")
        self.assertEqual(
            variants,
            [
                "تيرا برونز",
                "تيرا سينا",
                "تيرا يوجين",
                "تيرا ابرسيتي",
                "تيرا بلو",
                "تيرا سن بيرل",
                "تيرا اوسس بيرل",
                "تيرا تركواز",
            ],
        )
        self.assertNotIn("تيرا بلو / سينا / اوسن بيرل حرة", variants)
        self.assertIn("تيرا تركواز", variants)

    def test_captain_black_variants_after_cleanup(self):
        # حذفنا ٥ أصناف من "كابتن بلاك" (الاسم المباشر: ابيض/ازرق/ذهبي/
        # سليم/مسلف) — باقي الماركة (طويل × ٤ + كوين/سيجار يلو) ما تأثر.
        variants = cl.get_variants(self.catalog, "دخان", "كابتن بلاك")
        self.assertEqual(
            variants,
            [
                "كابتن بلاك طويل مانجو",
                "كابتن بلاك طويل شوكولا",
                "كابتن بلاك طويل تفاح",
                "كابتن بلاك طويل عنب",
                "كابتن كوين دهبي",
                "كابتن كوين ازرق",
                "كابتن كوين ون",
                "كابتن سليم فضي",
                "كابتن سلييم ازرق",
                "كابتن كوين ون اسود",
                "كابتن كوين ون ازرق",
                "سيجار يلو عنب",
                "سجار يلو سلفر",
                "سيجار يلو فريز",
                "سيجار يلو كرز",
                "سيجار يلو قهوة",
            ],
        )
        for old in ["كابتن بلاك ابيض", "كابتن بلاك ازرق", "كابتن بلاك ذهبي", "كابتن بلاك سليم", "كابتن بلاك مسلف"]:
            self.assertNotIn(old, variants, msg=old)

    def test_platinum_fadi_tawil_removed_but_tawil_fadi_kept(self):
        # صنفين متشابهين بالاسم بس بترتيب كلمات معاكس: "بلاتينيوم فضي طويل"
        # (محذوف) و"بلاتينيوم طويل فضي" (ضل موجود) — لازم ننتبه ما نحذف الغلط.
        variants = cl.get_variants(self.catalog, "دخان", "بلاتينيوم")
        self.assertNotIn("بلاتينيوم فضي طويل", variants)
        self.assertIn("بلاتينيوم طويل فضي", variants)

    def test_history_bare_variants_removed(self):
        # حذفنا "هيستوري طويل/قصير/سليم" (الأسماء المجردة بلا فضي/ازرق) —
        # الأصناف المفصّلة ضلت.
        variants = cl.get_variants(self.catalog, "دخان", "هيستوري")
        self.assertEqual(
            variants,
            [
                "هيستوري طويل فضي",
                "هيستوري طويل ازرق",
                "هيستوري قصير فضي",
                "هيستوري قصير ازرق",
                "هيستوري كوين",
                "هيستوري سليم فضي",
                "هيستوري سليم نعنع",
            ],
        )
        for old in ["هيستوري طويل", "هيستوري قصير", "هيستوري سليم"]:
            self.assertNotIn(old, variants, msg=old)

    def test_rose_bare_variants_removed(self):
        # حذفنا "روز طويل/قصير" المجردين و"روز سليم كومفورت / عادي" —
        # الأصناف المفصّلة (طويل فضي/ازرق، قصير ازرق/كولد/ابيض، سليم
        # فضي/بلوبيري، كلاسيك ابيض) ضلت.
        variants = cl.get_variants(self.catalog, "دخان", "روز")
        self.assertEqual(
            variants,
            [
                "روز طويل فضي",
                "روز طويل ازرق",
                "روز سليم فضي",
                "روز قصير ازرق",
                "روز قصير كولد",
                "روز قصير ابيض",
                "روز سليم بلوبيري",
                "روز كلاسيك ابيض",
            ],
        )
        for old in ["روز طويل", "روز قصير", "روز سليم كومفورت / عادي"]:
            self.assertNotIn(old, variants, msg=old)

    def test_every_type_has_at_least_one_real_variant(self):
        # بعكس البيانات القديمة، كل نوع (براند) هلق لازم يكون إلو صنف واحد عالأقل
        # حتى لو براند واحد بس إله صنف وحيد (متلاً "جيتان")، منشان حساب السعر
        # التلقائي يلاقي دايماً (نوع، صنف) يطابق سطر بملف الأسعار.
        for category in cl.get_categories(self.catalog):
            for type_ in cl.get_types(self.catalog, category):
                self.assertTrue(
                    cl.has_variants(self.catalog, category, type_),
                    f"{category} / {type_} ما إلو أصناف!",
                )

    def test_units_fixed_flag_for_cigarettes(self):
        units = cl.get_units(self.catalog, "دخان")
        names = {u["name"]: u["fixed"] for u in units}
        self.assertTrue(names["🥡 نص كروز"])
        self.assertFalse(names["🎁 كروز"])

    def test_bare_category_default_has_no_carton_unit(self):
        # وحدات القسم العامة (بلا تحديد نوع/ماركة) لسا بس كروز + نص كروز —
        # "كرتونة" منضافة بس عبر type_units (لكل ماركة على حدا)، شوف
        # test_every_cigarette_brand_has_carton_unit_with_default_50 تحت.
        units = cl.get_units(self.catalog, "دخان")
        names = {u["name"] for u in units}
        self.assertNotIn("📦📦 كرتونة", names)
        self.assertEqual(len(units), 2)

    def test_is_unit_fixed_helper(self):
        self.assertTrue(cl.is_unit_fixed(self.catalog, "دخان", "🥡 نص كروز"))
        self.assertFalse(cl.is_unit_fixed(self.catalog, "دخان", "🎁 كروز"))

    def test_dokhan_unit_multipliers(self):
        units = {u["name"]: u["multiplier"] for u in cl.get_units(self.catalog, "دخان")}
        self.assertEqual(units["🎁 كروز"], 1)
        self.assertEqual(units["🥡 نص كروز"], 0.5)

    def test_every_cigarette_brand_has_carton_unit_with_default_50(self):
        # كل ماركة دخان إلها رقم كرتونة (عدد الكروزات) لحالها بالكود، منشان
        # نقدر نصحح رقم ماركة وحدة بلا ما نأثر على الباقي لما توصلنا الأرقام
        # الحقيقية — مؤقتاً كلهن ٥٠ (قيمة افتراضية بالانتظار).
        for type_ in cl.get_types(self.catalog, "دخان"):
            units = {u["name"]: u for u in cl.get_units(self.catalog, "دخان", type_)}
            self.assertIn("📦📦 كرتونة", units, f"{type_} ما إلها خيار كرتونة!")
            carton = units["📦📦 كرتونة"]
            self.assertFalse(carton["fixed"])
            self.assertEqual(carton["multiplier"], 50)
            # الكروز ونص الكروز لازم يضلوا موجودين كمان جنب الكرتونة.
            self.assertIn("🎁 كروز", units)
            self.assertIn("🥡 نص كروز", units)

    def test_non_cigarette_categories_use_single_count_only_unit(self):
        # معسل/فحم/إكسسوارات/اراكيل إلكترونية: الحجم/الوزن مبيّن جوا اسم الصنف
        # نفسه أصلاً، فوحدتهن الوحيدة عدّاد بس (بلا تحويل وحدات).
        for category in ("معسل", "فحم", "إكسسوارات", "اراكيل الكترونية", "قداحات"):
            units = cl.get_units(self.catalog, category)
            self.assertEqual(len(units), 1)
            self.assertEqual(units[0]["name"], "🧮 عدد")
            self.assertFalse(units[0]["fixed"])
            self.assertEqual(units[0]["multiplier"], 1)

    def test_get_units_falls_back_to_category_default_when_no_override(self):
        default_units = cl.get_units(self.catalog, "معسل")
        units_for_type = cl.get_units(self.catalog, "معسل", "الفاخر")
        self.assertEqual(units_for_type, default_units)

    def test_get_units_uses_type_override_when_present(self):
        catalog = {
            "معسل": {
                "emoji": "💨",
                "types": {"براند بدون كيلو": ["صنف"]},
                "units": [
                    {"name": "علبة ٥٠غ", "fixed": False, "multiplier": 1},
                    {"name": "كيلو", "fixed": False, "multiplier": 1},
                ],
                "type_units": {
                    "براند بدون كيلو": [
                        {"name": "علبة ٥٠غ", "fixed": False, "multiplier": 1},
                    ]
                },
            }
        }
        override_units = cl.get_units(catalog, "معسل", "براند بدون كيلو")
        self.assertEqual([u["name"] for u in override_units], ["علبة ٥٠غ"])
        other_units = cl.get_units(catalog, "معسل", "براند تاني")
        self.assertEqual([u["name"] for u in other_units], ["علبة ٥٠غ", "كيلو"])

    def test_get_units_uses_variant_override_when_present_without_affecting_siblings(self):
        # كرتونة الفحم مضافة لصنف وحد محدد بس جوا الماركة (متلاً "كيلو")، مش لكل
        # أصناف الماركة — بعكس كرتونة الدخان يلي بتنطبق عالماركة كلها.
        catalog = {
            "فحم": {
                "emoji": "🔥",
                "types": {"ماركة فحم": ["فحم كيلو", "فحم نص كيلو"]},
                "units": [{"name": "🧮 عدد", "fixed": False, "multiplier": 1}],
                "variant_units": {
                    "ماركة فحم": {
                        "فحم كيلو": [
                            {"name": "🧮 عدد", "fixed": False, "multiplier": 1},
                            {"name": "📦📦 كرتونة", "fixed": False, "multiplier": 10},
                        ]
                    }
                },
            }
        }
        kilo_units = cl.get_units(catalog, "فحم", "ماركة فحم", "فحم كيلو")
        self.assertEqual(
            [u["name"] for u in kilo_units], ["🧮 عدد", "📦📦 كرتونة"]
        )
        half_kilo_units = cl.get_units(catalog, "فحم", "ماركة فحم", "فحم نص كيلو")
        self.assertEqual([u["name"] for u in half_kilo_units], ["🧮 عدد"])
        # وبلا variant، بيرجع الافتراضي العام (مش أي تسريب من صنف تاني).
        no_variant_units = cl.get_units(catalog, "فحم", "ماركة فحم")
        self.assertEqual([u["name"] for u in no_variant_units], ["🧮 عدد"])

    def test_every_charcoal_variant_has_carton_unit_kilo_10_others_50(self):
        # كل صنف فحم (أي برند، أي وزن) إلو خيار كرتونة/نص كرتونة بالإضافة
        # لـ"عدد" — أصناف الكيلو الكامل (كيلو/1 كغ/1000 غ) كرتونتها ١٠ علب،
        # وباقي الأوزان (نص كيلو، ربع كيلو، 250غ...) أو بلا وزن مكتوب أصلاً،
        # كرتونتها القياسية ٥٠ (نفس القياسي المعتمد بباقي الأقسام).
        kilo_variants = {
            ("سيبروس", "فحم سيبروس كيلو"),
            ("الزعيم", "فحم الزعيم كيلو"),
            ("الزعيم", "فحم الزعيم 1000 غ"),
            ("الزعيم", "فحم الزعيم 1 كغ"),
            ("يحيى كريستال", "فحم يحيى كريستال 1000 غ"),
            ("الاغا", "فحم الاغا 1 كغ"),
            ("كوكو 8", "فحم كوكو 8 1 كغ"),
            ("بيروتي", "فحم بيروتي 1 كغ"),
            ("فحم برو", "فحم برو 1 كغ"),
        }
        for brand in cl.get_types(self.catalog, "فحم"):
            for variant in cl.get_variants(self.catalog, "فحم", brand):
                units = {u["name"]: u for u in cl.get_units(self.catalog, "فحم", brand, variant)}
                expected_carton = 10 if (brand, variant) in kilo_variants else 50
                self.assertIn("📦📦 كرتونة", units, f"{brand} / {variant} ما إلها كرتونة!")
                self.assertFalse(units["📦📦 كرتونة"]["fixed"])
                self.assertEqual(
                    units["📦📦 كرتونة"]["multiplier"], expected_carton, f"{brand} / {variant}"
                )
                self.assertIn("🥡 نص كرتونة", units, f"{brand} / {variant} ما إلها نص كرتونة!")
                self.assertTrue(units["🥡 نص كرتونة"]["fixed"])
                self.assertEqual(
                    units["🥡 نص كرتونة"]["multiplier"], expected_carton / 2, f"{brand} / {variant}"
                )
                self.assertIn("🧮 عدد", units)


class TestExtractAmount(unittest.TestCase):
    def test_plain_western_digits(self):
        self.assertEqual(cl.extract_amount("70000"), 70000)

    def test_with_currency_words_around(self):
        self.assertEqual(cl.extract_amount("السعر 70000 ل.س صافي"), 70000)

    def test_arabic_indic_digits(self):
        self.assertEqual(cl.extract_amount("٧٠٠٠٠"), 70000)

    def test_thousands_separators_ignored(self):
        self.assertEqual(cl.extract_amount("100,000"), 100000)
        self.assertEqual(cl.extract_amount("100.000 ليرة"), 100000)

    def test_no_digits_returns_none(self):
        self.assertIsNone(cl.extract_amount("بكرا منحدد السعر"))

    def test_empty_returns_none(self):
        self.assertIsNone(cl.extract_amount(""))
        self.assertIsNone(cl.extract_amount(None))


class TestSplitDepositAmount(unittest.TestCase):
    def test_even_amount_splits_equally(self):
        self.assertEqual(cl.split_deposit_amount(70000), (35000, 35000))

    def test_odd_amount_sums_back_exactly(self):
        deposit, remaining = cl.split_deposit_amount(75001)
        self.assertEqual(deposit + remaining, 75001)
        self.assertEqual((deposit, remaining), (37500, 37501))


class TestParseCount(unittest.TestCase):
    def test_valid_western_digits(self):
        self.assertEqual(cl.parse_count("3"), 3)
        self.assertEqual(cl.parse_count("  12 "), 12)

    def test_valid_arabic_digits(self):
        self.assertEqual(cl.parse_count("٣"), 3)
        self.assertEqual(cl.parse_count("١٢"), 12)

    def test_invalid_inputs_return_none(self):
        self.assertIsNone(cl.parse_count("ثلاثة"))
        self.assertIsNone(cl.parse_count(""))
        self.assertIsNone(cl.parse_count("0"))
        self.assertIsNone(cl.parse_count("-5"))
        self.assertIsNone(cl.parse_count("3.5"))
        self.assertIsNone(cl.parse_count(None))


class TestQuantityFormatting(unittest.TestCase):
    def test_countable_unit(self):
        self.assertEqual(cl.format_quantity("باكيت", False, 3), "3 باكيت")

    def test_fixed_unit_ignores_count(self):
        self.assertEqual(cl.format_quantity("نص كروز", True), "نص كروز")

    def test_countable_unit_without_count_raises(self):
        with self.assertRaises(ValueError):
            cl.format_quantity("باكيت", False, None)


class TestCartOperations(unittest.TestCase):
    """
    السلة هلق لستة بُنى (dicts) بدل نصوص مباشرة — منشان نقدر نحسب سعر كل سطر
    تلقائياً (شوف cart_pricing.py) بدون ما نعيد تفكيك نص "display" المنسق.
    """

    def test_format_cart_line_with_variant_builds_structured_item(self):
        line = cl.format_cart_line("دخان", "ماستر", "ماستر طويل ورق م", "🎁 كروز", False, 3)
        self.assertEqual(line["display"], "▫️ دخان – ماستر – ماستر طويل ورق م – 3 🎁 كروز")
        self.assertEqual(line["category"], "دخان")
        self.assertEqual(line["type"], "ماستر")
        self.assertEqual(line["variant"], "ماستر طويل ورق م")
        self.assertEqual(line["unit_name"], "🎁 كروز")
        self.assertFalse(line["unit_fixed"])
        self.assertEqual(line["count"], 3)

    def test_format_cart_line_fixed_unit_has_no_count_in_display(self):
        line = cl.format_cart_line("دخان", "ماستر", "ماستر طويل ورق م", "🥡 نص كروز", True, None)
        self.assertEqual(line["display"], "▫️ دخان – ماستر – ماستر طويل ورق م – 🥡 نص كروز")
        self.assertIsNone(line["count"])

    def test_format_cart_line_without_variant(self):
        line = cl.format_cart_line("فحم", "فحم", None, "🧮 عدد", False, 2)
        self.assertEqual(line["display"], "▫️ فحم – فحم – 2 🧮 عدد")
        self.assertIsNone(line["variant"])

    def test_add_to_cart_with_variant(self):
        line = cl.format_cart_line("دخان", "ماستر", "ماستر طويل ورق م", "🎁 كروز", False, 3)
        cart, backup = cl.add_to_cart([], line)
        self.assertEqual(cart, [line])
        self.assertEqual(backup, [])

    def test_added_summary_without_variant(self):
        summary = cl.format_added_summary("فحم", None, "2 🧮 عدد")
        self.assertEqual(summary, "فحم – 2 🧮 عدد")

    def test_undo_last_reverts_one_step_only(self):
        line1 = cl.format_cart_line("دخان", "ماستر", "ماستر طويل ورق م", "🎁 كروز", False, 3)
        cart1, backup1 = cl.add_to_cart([], line1)
        line2 = cl.format_cart_line("معسل", "الفاخر", "الفاخر علكة", "🧮 عدد", False, 2)
        cart2, backup2 = cl.add_to_cart(cart1, line2)

        self.assertEqual(cart2, [line1, line2])
        reverted = cl.undo_last(backup2)
        self.assertEqual(reverted, [line1])

    def test_clear_cart(self):
        cart, backup = cl.clear_cart()
        self.assertEqual(cart, [])
        self.assertEqual(backup, [])

    def test_format_cart_text_empty(self):
        self.assertEqual(cl.format_cart_text([]), "(السلة لسا فاضية)")

    def test_format_cart_text_joins_structured_lines(self):
        line1 = cl.format_cart_line("دخان", "ماستر", "ماستر طويل ورق م", "🎁 كروز", False, 3)
        line2 = cl.format_cart_line("فحم", "فحم", None, "🧮 عدد", False, 2)
        text = cl.format_cart_text([line1, line2])
        self.assertEqual(text, f"{line1['display']}\n{line2['display']}")

    def test_format_cart_text_backward_compatible_with_old_plain_string_lines(self):
        # طلبات قديمة محفوظة (orders_log.json) من قبل هالتحديث كانت سلتها نصوص
        # مباشرة (list[str]) — لازم تضل تنعرض صح.
        text = cl.format_cart_text(["▫️ أ", "▫️ ب"])
        self.assertEqual(text, "▫️ أ\n▫️ ب")

    def test_format_priced_cart_text_appends_price_per_line(self):
        line1 = cl.format_cart_line("دخان", "ماستر", "ماستر طويل ورق م", "🎁 كروز", False, 3)
        line2 = cl.format_cart_line("فحم", "فحم", None, "🧮 عدد", False, 2)
        text = cl.format_priced_cart_text([line1, line2], [201000, 63000])
        self.assertEqual(
            text,
            f"{line1['display']} — 201000 ل.س\n{line2['display']} — 63000 ل.س",
        )

    def test_format_priced_cart_text_empty(self):
        self.assertEqual(cl.format_priced_cart_text([], []), "(السلة لسا فاضية)")


if __name__ == "__main__":
    unittest.main()
