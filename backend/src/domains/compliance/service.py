"""Compliance Service managing developer guidelines, pitfall cases, and self-audit radar."""
from typing import List
from src.domains.compliance.models import (
    ComplianceDimension,
    ComplianceCase,
    AuditCheckItem,
    AuditEvaluateRequest,
    AuditReportResponse,
)


class ComplianceService:
    """Provides product compliance knowledge and evaluates maker self-audit checklists."""

    def __init__(self):
        self._dimensions: List[ComplianceDimension] = []
        self._cases: List[ComplianceCase] = []
        self._checkpoints: List[AuditCheckItem] = []

    def _build_dimensions(self) -> List[ComplianceDimension]:
        return [
            ComplianceDimension(
                id="dim_privacy",
                title="个人信息与隐私安全",
                summary="用户数据最小必要收集、明示授权同意与注销遗忘通道",
                core_rules=[
                    "严禁未经用户明示授权静默读取剪贴板、手机号、相册等敏感信息",
                    "必须在登录/注册显要位置展示《隐私政策》，严禁默认勾选授权",
                    "必须在产品前台提供清晰、可执行的账号安全注销通道，并完成脱敏销毁",
                ],
                penalties="通报批评、下架整改、处五千万元以下或上一年度营业额百分之五以下罚款",
                law_ref="《中华人民共和国个人信息保护法》第十三条、第四十七条",
                icon_name="shield",
            ),
            ComplianceDimension(
                id="dim_payment",
                title="资金结算防二清红线",
                summary="严禁自建平台资金池，必须接入持牌机构分账",
                core_rules=[
                    "平台绝不得作为资金出纳方沉淀用户充值或撮合佣金款项",
                    "多方分账交易必须对接微信支付分账、支付宝商户分账或商业银行托管通道",
                    "严禁通过个人银行卡、微信零钱大额归集转账或隐蔽变相二次清算",
                ],
                penalties="以非法吸收公众存款罪或非法经营罪追究刑事责任，没收违法所得",
                law_ref="中国人民银行《关于规范非银行支付机构客户备付金存管办法》",
                icon_name="credit-card",
            ),
            ComplianceDimension(
                id="dim_filing",
                title="资质许可与上线备案",
                summary="工信部ICP备案、公安网安备案与生成式AI算法备案",
                core_rules=[
                    "域名及服务器在国内必须办理工信部 ICP 备案，涉及经营性电商须申领 EDI 许可证",
                    "网站或 App 开通之日起 30 日内必须在全国公安机关互联网站安全管理平台完成网安备案",
                    "调用或微调大模型面向公众提供文本/代码/图像生成服务，必须在网信办完成算法备案",
                ],
                penalties="域名解析阻断、服务器下线关停、最高一百万元罚款",
                law_ref="《生成式人工智能服务管理暂行办法》第十七条、《互联网信息服务管理办法》第四条",
                icon_name="file-text",
            ),
            ComplianceDimension(
                id="dim_ip_oss",
                title="知识产权与开源合规",
                summary="严防强传染开源许可证感染商业闭源源码，保护商誉商标",
                core_rules=[
                    "使用 GPL / AGPL 协议的开源组件时，严禁与私有闭源业务逻辑直接静态编译或强耦合",
                    "第三方 SDK 与字体/素材图标需确保具备合法商业授权，留存采购发票与授权书",
                    "及时申请核心软件著作权登记与国家知识产权局第 9 类/第 42 类商标保护",
                ],
                penalties="侵权赔偿最高五百万元法定赔偿，法院强制判令开源核心闭源业务代码",
                law_ref="《中华人民共和国著作权法》第四十九条、开源许可证违约司法裁判规则",
                icon_name="code",
            ),
            ComplianceDimension(
                id="dim_cross_border",
                title="数据出境与海外合规",
                summary="出海 SaaS 必须遵循 GDPR / CCPA 与海外纳税结汇监管",
                core_rules=[
                    "出海产品若涉及欧盟公民个人数据，必须严格遵循 GDPR，设立 DPO 角色并支持数据可携",
                    "境外收入结汇至境内必须依托合法跨境外汇支付牌照，提供真实物流/服务贸易合同凭证",
                    "向境外传输重要业务数据前，需评估数据出境安全自评估及订立标准合同",
                ],
                penalties="最高达全球年营业额 4% 或 2000 万欧元的巨额 GDPR 行政罚单",
                law_ref="欧盟《通用数据保护条例》(GDPR)、我国《数据出境安全评估办法》",
                icon_name="globe",
            ),
            ComplianceDimension(
                id="dim_ugc_security",
                title="UGC 内容安全与留痕",
                summary="后台实名、前台IP属地公开、敏感词防御与180天日志",
                core_rules=[
                    "前台社区帖子与楼中楼评论强制展示发帖人所在省份或境外国家/地区 IP 属地",
                    "接入敏感词 Trie 树实时校验，一级涉黄/涉恐/涉诈/违法黑产直接拒绝提交",
                    "依法对系统网络访问日志、用户行为操作审计记录加密留存不少于 180 天",
                ],
                penalties="网信办通报下架、停机整顿直至注销电信业务许可证",
                law_ref="《中华人民共和国网络安全法》第二十一条、《互联网用户账号信息管理规定》第十二条",
                icon_name="alert-triangle",
            ),
        ]

    def _build_cases(self) -> List[ComplianceCase]:
        return [
            ComplianceCase(
                id="case_01",
                title="某知名独立开发者工具因内嵌资金池涉二清被微信冻结",
                industry="微支付 / 工具聚合",
                violation="私设收款中转池，商户充值款沉淀个人账户后再手工转账给外包团队",
                consequence="商户号被微信支付风控体系永久冻结，冻结沉淀资金 68 万元并处没收",
                lesson="所有撮合交易或创客分成，必须全量接入持牌机构商户分账（如微信分账、支付宝直付通），平台碰不到资金。",
                badge_color="#ef4444",
            ),
            ComplianceCase(
                id="case_02",
                title="某海外出海 SaaS 因未提供数据注销通道被欧盟 GDPR 重罚",
                industry="出海生产力工具",
                violation="产品仅提供退出登录，用户发邮件请求删除账号与历史数据遭无视逾 30 天",
                consequence="被欧盟数据保护专员处以 12 万欧元罚款并限制在法德两国 App Store 展业",
                lesson="产品上线必须前置集成“账号安全注销通道”，用户确认后必须在底层物理脱敏或销毁其个人身份信息。",
                badge_color="#f97316",
            ),
            ComplianceCase(
                id="case_03",
                title="某开源商业软件误用 AGPL 模块被判强制开源核心代码",
                industry="企业级应用",
                violation="在商业闭源微服务中直接静态引入某开源 AGPL-3.0 协议分析库，未履行开源义务",
                consequence="被开源原作者提请知识产权诉讼，法院裁定侵权，判令限期开源该闭源服务全套源码",
                lesson="建立代码库依赖开源许可证扫描机制，商业闭源项目严格排查 GPL / AGPL 强传染性许可证，优先选用 MIT / Apache-2.0。",
                badge_color="#eab308",
            ),
        ]

    def _build_checkpoints(self) -> List[AuditCheckItem]:
        return [
            AuditCheckItem(
                id="chk_01",
                dimension_id="dim_privacy",
                title="用户登录/注册是否明确展示《隐私政策》且未默认勾选？",
                description="明示知情同意是信息收集的第一法定红线，禁止任何形式的默认静默授权。",
                severity="CRITICAL",
                weight=12,
                advice="在注册表单移除默认 checked 属性，用户未主动勾选时点击注册弹出温和确认框。",
                legal_basis="《个人信息保护法》第十三条",
            ),
            AuditCheckItem(
                id="chk_02",
                dimension_id="dim_privacy",
                title="用户中心是否提供明确、可随时操作的【注销账号】通道？",
                description="用户享有法定数据遗忘权，产品必须提供自主注销入口并完成脱敏。",
                severity="HIGH",
                weight=10,
                advice="在个人设置中心挂载注销通道，注销前核实身份，注销后不可逆匿名化留存必要审计数据。",
                legal_basis="《个人信息保护法》第四十七条",
            ),
            AuditCheckItem(
                id="chk_03",
                dimension_id="dim_payment",
                title="平台资金是否由持牌支付机构托管，绝无自建资金池？",
                description="平台作为撮合中介绝对不可作为资金中转结算方，严防二清法律责任。",
                severity="CRITICAL",
                weight=15,
                advice="全面对接微信分账、支付宝服务商分账或商业银行托管账户，所有收付款直达持牌通道。",
                legal_basis="《非银行支付机构客户备付金存管办法》",
            ),
            AuditCheckItem(
                id="chk_04",
                dimension_id="dim_filing",
                title="境内上线的服务是否已完成工信部 ICP 与公安网安备案？",
                description="未备案网站不得从事互联网信息服务，30日内必须完成公安联网备案。",
                severity="HIGH",
                weight=10,
                advice="完成管局 ICP 审核后，在全国公安互联网站安全管理平台登记备案并在页脚悬挂号牌。",
                legal_basis="《互联网信息服务管理办法》第四条",
            ),
            AuditCheckItem(
                id="chk_05",
                dimension_id="dim_filing",
                title="面向公众提供的 AI 生成式功能是否完成了网信办算法备案？",
                description="提供基于大模型深度合成的内容生成、代码辅助服务须履行算法备案义务。",
                severity="HIGH",
                weight=10,
                advice="若调用第三方大模型需取得其商用授权，自研或微调须在网信办算法备案系统填报。",
                legal_basis="《生成式人工智能服务管理暂行办法》第十七条",
            ),
            AuditCheckItem(
                id="chk_06",
                dimension_id="dim_ip_oss",
                title="项目代码库是否排查过 GPL / AGPL 强传染开源协议？",
                description="强传染协议会导致商业闭源产品依法被强制开源其衍生工程全部代码。",
                severity="CRITICAL",
                weight=12,
                advice="使用许可证扫描工具排查依赖，将 GPL/AGPL 组件替换为 MIT、Apache-2.0 或通过微服务进程隔离。",
                legal_basis="《中华人民共和国著作权法》",
            ),
            AuditCheckItem(
                id="chk_07",
                dimension_id="dim_ugc_security",
                title="社区发帖与评论是否强制公开展示发帖人 IP 属地？",
                description="依国家规定境内展示至省份/直辖市，境外展示至国家或地区，用户不可自主关闭。",
                severity="HIGH",
                weight=8,
                advice="服务端接收请求提取来源 IP 并解析省份，直接固化在帖子与评论的数据模型中展示。",
                legal_basis="《互联网用户账号信息管理规定》第十二条",
            ),
            AuditCheckItem(
                id="chk_08",
                dimension_id="dim_ugc_security",
                title="发帖与交互前置是否集成了敏感词过滤与一键举报闭环？",
                description="一级涉黄暴恐诈骗敏感词需直接阻断提交，前台每张卡片均需挂载举报入口。",
                severity="HIGH",
                weight=10,
                advice="在服务端网关接入 Trie 树敏感词过滤中间件，前台提供直通内容治理控制台的一键举报按钮。",
                legal_basis="《网络安全法》第十二条",
            ),
            AuditCheckItem(
                id="chk_09",
                dimension_id="dim_ugc_security",
                title="用户访问、发帖操作审计日志是否落实加密保存 180 天？",
                description="网络安全法强制规定提供公共信息服务的日志记录必须留存不少于 6 个月。",
                severity="MEDIUM",
                weight=5,
                advice="数据库或归档对象存储配置冷热备份策略，日志保留策略设置为不少于 180 天。",
                legal_basis="《网络安全法》第二十一条",
            ),
            AuditCheckItem(
                id="chk_10",
                dimension_id="dim_cross_border",
                title="出海面向境外用户的产品是否完成了 GDPR / CCPA 隐私合规梳理？",
                description="出海产品涉及海外用户个人信息时，需提供合规隐私声明与数据出境自评估。",
                severity="MEDIUM",
                weight=8,
                advice="起草多语言隐私条款，配置境外 CDN 节点隔离存储，并在需求集市对接资深涉外法务顾问。",
                legal_basis="欧盟 GDPR 标准合同条款 (SCC)",
            ),
        ]

    def get_dimensions(self) -> List[ComplianceDimension]:
        return self._dimensions

    def get_cases(self) -> List[ComplianceCase]:
        return self._cases

    def get_checkpoints(self) -> List[AuditCheckItem]:
        return self._checkpoints

    def evaluate_audit(self, req: AuditEvaluateRequest) -> AuditReportResponse:
        passed_set = set(req.passed_item_ids)
        total_weight = sum(item.weight for item in self._checkpoints)
        earned_weight = sum(item.weight for item in self._checkpoints if item.id in passed_set)

        score = int(round((earned_weight / total_weight) * 100)) if total_weight > 0 else 0
        failed_items = [item for item in self._checkpoints if item.id not in passed_set]

        if score >= 90:
            grade = "EXCELLENT"
        elif score >= 75:
            grade = "GOOD"
        elif score >= 60:
            grade = "WARNING"
        else:
            grade = "CRITICAL"

        suggestions = [item.advice for item in failed_items]
        legal_help_needed = None
        if failed_items:
            # Generate tailored demand recommendation
            legal_help_needed = f"检测到 {len(failed_items)} 个合规风险点（特别是 {failed_items[0].title}），建议前往需求集市发布专项法律求助或咨询法务服务商。"

        return AuditReportResponse(
            score=score,
            grade=grade,
            total_items=len(self._checkpoints),
            passed_items_count=len(self._checkpoints) - len(failed_items),
            failed_items_count=len(failed_items),
            risk_items=failed_items,
            remedy_suggestions=suggestions,
            legal_help_recommendation=legal_help_needed,
        )


compliance_service = ComplianceService()
