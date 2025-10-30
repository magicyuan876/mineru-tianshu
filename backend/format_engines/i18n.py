"""
Internationalization (i18n) Module for Format Engines
国际化模块 - 支持多语言语义描述生成
"""

from typing import Dict, Any
from enum import Enum


class Language(str, Enum):
    """支持的语言"""

    EN = "en"
    ZH = "zh"


class I18nTemplate:
    """国际化模板基类"""

    def __init__(self, lang: Language = Language.EN):
        self.lang = lang

    def get(self, key: str, **kwargs) -> str:
        """
        获取国际化文本

        Args:
            key: 文本键
            **kwargs: 格式化参数

        Returns:
            格式化后的文本
        """
        templates = self._get_templates()
        template = templates.get(self.lang, {}).get(key, templates[Language.EN].get(key, key))
        return template.format(**kwargs) if kwargs else template

    def _get_templates(self) -> Dict[Language, Dict[str, str]]:
        """获取所有模板（子类实现）"""
        raise NotImplementedError


class NucleotideSemantics(I18nTemplate):
    """核酸序列语义描述模板"""

    def _get_templates(self) -> Dict[Language, Dict[str, str]]:
        return {
            Language.EN: {
                # GC content
                "at_rich": "This is an AT-rich sequence (GC content {gc:.1f}%), likely from AT-rich genomic regions",
                "gc_rich": "This is a GC-rich sequence (GC content {gc:.1f}%), potentially encoding structural genes or promoter regions",
                "moderate_gc": "This sequence has moderate GC content ({gc:.1f}%)",
                # ORF
                "long_orf": "Long open reading frame detected ({length} bp), potentially encoding a functional protein",
                "moderate_orf": "Contains a moderate-length open reading frame ({length} bp)",
                # CpG islands
                "cpg_islands": "Identified {count} CpG island(s), potentially associated with gene regulation",
                # Repeats
                "repeats": "Found {count} repeat sequence(s), possibly with structural or regulatory functions",
                # Complexity
                "low_complexity": "Low sequence complexity, likely a simple repeat or low-complexity region",
                "high_complexity": "High sequence complexity with rich information content",
                # Separator
                "separator": "; ",
                "terminator": ".",
            },
            Language.ZH: {
                # GC 含量
                "at_rich": "该序列为 AT 富集序列（GC含量 {gc:.1f}%），可能来自 AT 富集的基因组区域",
                "gc_rich": "该序列为 GC 富集序列（GC含量 {gc:.1f}%），可能编码结构基因或启动子区域",
                "moderate_gc": "该序列具有中等 GC 含量（{gc:.1f}%）",
                # ORF
                "long_orf": "检测到长开放阅读框（{length} bp），可能编码功能蛋白",
                "moderate_orf": "包含中等长度的开放阅读框（{length} bp）",
                # CpG 岛
                "cpg_islands": "检测到 {count} 个 CpG 岛，可能与基因调控相关",
                # 重复序列
                "repeats": "发现 {count} 处重复序列，可能具有结构或调控功能",
                # 复杂度
                "low_complexity": "序列复杂度较低，可能为简单重复或低复杂度区域",
                "high_complexity": "序列复杂度高，信息含量丰富",
                # 分隔符
                "separator": "；",
                "terminator": "。",
            },
        }


class ProteinSemantics(I18nTemplate):
    """蛋白质序列语义描述模板"""

    def _get_templates(self) -> Dict[Language, Dict[str, str]]:
        return {
            Language.EN: {
                # Stability
                "stability": "This protein is predicted to be {stability} (instability index {index:.1f})",
                # Isoelectric point
                "pi_acidic": "Isoelectric point {pi:.2f}, acidic protein",
                "pi_basic": "Isoelectric point {pi:.2f}, basic protein",
                "pi_neutral": "Isoelectric point {pi:.2f}, neutral protein",
                # Hydropathy
                "hydrophobic": "GRAVY score {gravy:.2f}, hydrophobic protein, likely a membrane protein",
                "hydrophilic": "GRAVY score {gravy:.2f}, hydrophilic protein",
                # Secondary structure
                "secondary_structure": "Secondary structure prediction: α-helix {helix:.1f}%, β-sheet {sheet:.1f}%",
                # Amino acid composition
                "aa_composition": "Amino acid composition: hydrophobic {hydrophobic:.1f}%, positively charged {positive:.1f}%, negatively charged {negative:.1f}%",
                # PTM sites
                "ptm_sites": "Identified {count} potential phosphorylation site(s)",
                # Separator
                "separator": "; ",
                "terminator": ".",
            },
            Language.ZH: {
                # 稳定性
                "stability": "该蛋白质预测为 {stability}（不稳定指数 {index:.1f}）",
                # 等电点
                "pi_acidic": "等电点 {pi:.2f}，为酸性蛋白",
                "pi_basic": "等电点 {pi:.2f}，为碱性蛋白",
                "pi_neutral": "等电点 {pi:.2f}，为中性蛋白",
                # 疏水性
                "hydrophobic": "GRAVY 值 {gravy:.2f}，为疏水性蛋白，可能为膜蛋白",
                "hydrophilic": "GRAVY 值 {gravy:.2f}，为亲水性蛋白",
                # 二级结构
                "secondary_structure": "二级结构预测：α-螺旋 {helix:.1f}%，β-折叠 {sheet:.1f}%",
                # 氨基酸组成
                "aa_composition": "氨基酸组成：疏水性 {hydrophobic:.1f}%，正电荷 {positive:.1f}%，负电荷 {negative:.1f}%",
                # PTM 位点
                "ptm_sites": "检测到 {count} 个潜在磷酸化位点",
                # 分隔符
                "separator": "；",
                "terminator": "。",
            },
        }


class CommonSemantics(I18nTemplate):
    """通用语义描述模板"""

    def _get_templates(self) -> Dict[Language, Dict[str, str]]:
        return {
            Language.EN: {
                # Titles
                "fasta_title": "FASTA Sequence Analysis Results",
                "genbank_title": "GenBank Sequence Analysis Results",
                # Summary
                "empty_file": "Empty file, no sequences found",
                "sequence_summary": "Contains {count} biological sequence(s), total length {length:,} bp",
                "genbank_summary": "Contains {count} GenBank record(s), total length {length:,} bp",
                "genbank_summary_with_features": "Contains {count} GenBank record(s), total length {length:,} bp, with {features} feature annotations",
                # Statistics
                "statistics": "Statistics",
                "sequence_count": "Sequence Count",
                "total_length": "Total Length",
                "average_length": "Average Length",
                "shortest_sequence": "Shortest Sequence",
                "longest_sequence": "Longest Sequence",
                # Details
                "sequence_details": "Sequence Details",
                "biological_significance": "Biological Significance",
                "sequence_preview": "Sequence Preview",
                "gc_content": "GC Content",
                "longest_orf": "Longest ORF",
                "cpg_islands": "CpG Islands",
                "sequence_complexity": "Sequence Complexity",
                "molecular_weight": "Molecular Weight",
                "isoelectric_point": "Isoelectric Point",
                "stability": "Stability",
                "hydropathy": "Hydropathy (GRAVY)",
                "secondary_structure": "Secondary Structure Prediction",
            },
            Language.ZH: {
                # 标题
                "fasta_title": "FASTA 序列解析结果",
                "genbank_title": "GenBank 序列解析结果",
                # 摘要
                "empty_file": "空文件，未找到任何序列",
                "sequence_summary": "包含 {count} 条生物序列，总长度 {length:,} bp",
                "genbank_summary": "包含 {count} 条 GenBank 记录，总长度 {length:,} bp",
                "genbank_summary_with_features": "包含 {count} 条 GenBank 记录，总长度 {length:,} bp，共 {features} 个特征注释",
                # 统计
                "statistics": "统计信息",
                "sequence_count": "序列数量",
                "total_length": "总长度",
                "average_length": "平均长度",
                "shortest_sequence": "最短序列",
                "longest_sequence": "最长序列",
                # 详情
                "sequence_details": "序列详情",
                "biological_significance": "生物学意义",
                "sequence_preview": "序列预览",
                "gc_content": "GC 含量",
                "longest_orf": "最长 ORF",
                "cpg_islands": "CpG 岛数量",
                "sequence_complexity": "序列复杂度",
                "molecular_weight": "分子量",
                "isoelectric_point": "等电点",
                "stability": "稳定性",
                "hydropathy": "疏水性 (GRAVY)",
                "secondary_structure": "二级结构预测",
            },
        }


class SemanticGenerator:
    """语义描述生成器 - 核心业务逻辑"""

    def __init__(self, lang: Language = Language.EN):
        self.lang = lang
        self.nucleotide_i18n = NucleotideSemantics(lang)
        self.protein_i18n = ProteinSemantics(lang)
        self.common_i18n = CommonSemantics(lang)

    def generate_nucleotide_semantics(self, analysis: Dict[str, Any]) -> str:
        """
        生成核酸序列的语义描述（增强版 - 包含更多领域知识）

        Args:
            analysis: 分析结果字典

        Returns:
            语义描述文本
        """
        parts = []

        # GC 含量解释（更详细）
        gc = analysis.get("gc_content", 0) * 100
        if gc < 30:
            # 极低 GC 含量
            if self.lang == Language.ZH:
                parts.append(f"该序列为极低 GC 序列（GC含量 {gc:.1f}%），可能来自寄生生物或极端环境微生物")
            else:
                parts.append(
                    f"This is an extremely AT-rich sequence (GC content {gc:.1f}%), possibly from parasitic organisms or extremophiles"
                )
        elif gc < 40:
            parts.append(self.nucleotide_i18n.get("at_rich", gc=gc))
        elif gc > 70:
            # 极高 GC 含量
            if self.lang == Language.ZH:
                parts.append(f"该序列为极高 GC 序列（GC含量 {gc:.1f}%），常见于放线菌或某些植物基因组")
            else:
                parts.append(
                    f"This is an extremely GC-rich sequence (GC content {gc:.1f}%), common in actinomycetes or certain plant genomes"
                )
        elif gc > 60:
            parts.append(self.nucleotide_i18n.get("gc_rich", gc=gc))
        else:
            parts.append(self.nucleotide_i18n.get("moderate_gc", gc=gc))

        # GC 偏斜度（新增）
        gc_skew = analysis.get("gc_skew")
        if gc_skew is not None and abs(gc_skew) > 0.15:
            if self.lang == Language.ZH:
                skew_type = "正向" if gc_skew > 0 else "负向"
                parts.append(f"GC 偏斜度显著（{gc_skew:.2f}，{skew_type}），可能指示 DNA 复制起点或链特异性")
            else:
                skew_type = "positive" if gc_skew > 0 else "negative"
                parts.append(
                    f"Significant GC skew ({gc_skew:.2f}, {skew_type}), may indicate replication origin or strand bias"
                )

        # ORF 信息（更智能的判断）
        longest_orf = analysis.get("longest_orf_length", 0)
        orf_count = len(analysis.get("orfs", []))

        if longest_orf >= 1000:
            # 很长的 ORF
            if self.lang == Language.ZH:
                parts.append(f"检测到长开放阅读框（{longest_orf} bp），高度可能编码大型蛋白质或基因")
            else:
                parts.append(
                    f"Long open reading frame detected ({longest_orf} bp), highly likely to encode a large protein or gene"
                )
        elif longest_orf >= 300:
            parts.append(self.nucleotide_i18n.get("long_orf", length=longest_orf))
            if orf_count > 1:
                if self.lang == Language.ZH:
                    parts.append(f"共检测到 {orf_count} 个 ORF，可能包含多个基因或操纵子")
                else:
                    parts.append(f"Total {orf_count} ORFs detected, may contain multiple genes or operons")
        elif longest_orf >= 100:
            parts.append(self.nucleotide_i18n.get("moderate_orf", length=longest_orf))

        # CpG 岛（更详细的解释）
        cpg_islands = analysis.get("cpg_islands", [])
        if cpg_islands:
            island_count = len(cpg_islands)
            if island_count > 3:
                if self.lang == Language.ZH:
                    parts.append(f"检测到多个 CpG 岛（{island_count} 个），高度提示基因启动子区域或 CpG 岛岸区")
                else:
                    parts.append(
                        f"Multiple CpG islands detected ({island_count}), strong indication of gene promoter regions or CGI shores"
                    )
            else:
                parts.append(self.nucleotide_i18n.get("cpg_islands", count=island_count))

        # 重复序列（更详细）
        repeats = analysis.get("repeats", [])
        if repeats:
            repeat_count = len(repeats)
            if repeat_count > 5:
                if self.lang == Language.ZH:
                    parts.append(f"发现大量重复序列（{repeat_count} 处），可能为卫星 DNA、微卫星或转座子元件")
                else:
                    parts.append(
                        f"Numerous repeat sequences found ({repeat_count}), possibly satellite DNA, microsatellites, or transposable elements"
                    )
            else:
                parts.append(self.nucleotide_i18n.get("repeats", count=repeat_count))

        # 序列复杂度（更精确的解释）
        entropy = analysis.get("sequence_entropy", 0)
        if entropy < 1.0:
            if self.lang == Language.ZH:
                parts.append("序列复杂度极低，可能为同聚物或简单重复序列")
            else:
                parts.append("Extremely low sequence complexity, likely homopolymer or simple repeat")
        elif entropy < 1.5:
            parts.append(self.nucleotide_i18n.get("low_complexity"))
        elif entropy > 1.9:
            parts.append(self.nucleotide_i18n.get("high_complexity"))

        # 连接并返回
        separator = self.nucleotide_i18n.get("separator")
        terminator = self.nucleotide_i18n.get("terminator")
        return separator.join(parts) + terminator

    def generate_protein_semantics(self, analysis: Dict[str, Any]) -> str:
        """
        生成蛋白质序列的语义描述（增强版 - 包含更多领域知识）

        Args:
            analysis: 分析结果字典

        Returns:
            语义描述文本
        """
        parts = []

        # 分子量（新增）
        mw = analysis.get("molecular_weight", 0)
        if mw > 0:
            mw_kda = mw / 1000
            if self.lang == Language.ZH:
                if mw_kda > 100:
                    parts.append(f"大型蛋白质，分子量 {mw_kda:.1f} kDa")
                elif mw_kda < 10:
                    parts.append(f"小分子多肽，分子量 {mw_kda:.1f} kDa")
                else:
                    parts.append(f"分子量 {mw_kda:.1f} kDa")
            else:
                if mw_kda > 100:
                    parts.append(f"Large protein, molecular weight {mw_kda:.1f} kDa")
                elif mw_kda < 10:
                    parts.append(f"Small peptide, molecular weight {mw_kda:.1f} kDa")
                else:
                    parts.append(f"Molecular weight {mw_kda:.1f} kDa")

        # 稳定性（增强解释）
        stability = analysis.get("stability_class", "unknown")
        instability = analysis.get("instability_index", 0)

        if instability < 25:
            if self.lang == Language.ZH:
                parts.append(f"高度稳定（不稳定指数 {instability:.1f}），适合体外表达和纯化")
            else:
                parts.append(
                    f"Highly stable (instability index {instability:.1f}), suitable for in vitro expression and purification"
                )
        elif instability < 40:
            parts.append(self.protein_i18n.get("stability", stability=stability, index=instability))
        else:
            if self.lang == Language.ZH:
                parts.append(f"不稳定（不稳定指数 {instability:.1f}），可能需要特殊处理或快速处理")
            else:
                parts.append(
                    f"Unstable (instability index {instability:.1f}), may require special handling or rapid processing"
                )

        # 等电点（增强解释）
        pi = analysis.get("isoelectric_point", 0)
        if pi < 5:
            if self.lang == Language.ZH:
                parts.append(f"强酸性蛋白（等电点 {pi:.2f}），可能富含天冬氨酸和谷氨酸")
            else:
                parts.append(f"Strong acidic protein (pI {pi:.2f}), likely rich in aspartic and glutamic acids")
        elif pi < 6:
            parts.append(self.protein_i18n.get("pi_acidic", pi=pi))
        elif pi > 9:
            if self.lang == Language.ZH:
                parts.append(f"强碱性蛋白（等电点 {pi:.2f}），可能富含赖氨酸和精氨酸")
            else:
                parts.append(f"Strong basic protein (pI {pi:.2f}), likely rich in lysine and arginine")
        elif pi > 8:
            parts.append(self.protein_i18n.get("pi_basic", pi=pi))
        else:
            parts.append(self.protein_i18n.get("pi_neutral", pi=pi))

        # 疏水性（增强解释）
        gravy = analysis.get("gravy", 0)
        if gravy > 0.5:
            if self.lang == Language.ZH:
                parts.append(f"高度疏水性蛋白（GRAVY {gravy:.2f}），很可能为跨膜蛋白或膜结合蛋白")
            else:
                parts.append(
                    f"Highly hydrophobic protein (GRAVY {gravy:.2f}), very likely transmembrane or membrane-associated protein"
                )
        elif gravy > 0:
            parts.append(self.protein_i18n.get("hydrophobic", gravy=gravy))
        elif gravy < -0.5:
            if self.lang == Language.ZH:
                parts.append(f"高度亲水性蛋白（GRAVY {gravy:.2f}），可能为分泌蛋白或细胞外蛋白")
            else:
                parts.append(
                    f"Highly hydrophilic protein (GRAVY {gravy:.2f}), possibly secreted or extracellular protein"
                )
        else:
            parts.append(self.protein_i18n.get("hydrophilic", gravy=gravy))

        # 二级结构（增强解释）
        ss = analysis.get("secondary_structure", {})
        helix = ss.get("helix", 0) * 100
        sheet = ss.get("sheet", 0) * 100

        if helix > 40:
            if self.lang == Language.ZH:
                parts.append(f"富含 α-螺旋（{helix:.1f}%），可能为螺旋束蛋白或 DNA 结合蛋白")
            else:
                parts.append(f"Rich in α-helix ({helix:.1f}%), possibly helical bundle or DNA-binding protein")
        elif sheet > 30:
            if self.lang == Language.ZH:
                parts.append(f"富含 β-折叠（{sheet:.1f}%），可能为 β-桶状蛋白或淀粉样蛋白")
            else:
                parts.append(f"Rich in β-sheet ({sheet:.1f}%), possibly β-barrel or amyloid protein")
        else:
            parts.append(self.protein_i18n.get("secondary_structure", helix=helix, sheet=sheet))

        # 芳香性（新增）
        aromaticity = analysis.get("aromaticity", 0)
        if aromaticity > 0.15:
            if self.lang == Language.ZH:
                parts.append(f"高芳香性（{aromaticity*100:.1f}%），可能包含重要的芳香族残基簇")
            else:
                parts.append(
                    f"High aromaticity ({aromaticity*100:.1f}%), may contain important aromatic residue clusters"
                )

        # 潜在修饰位点（增强）
        ptm = analysis.get("ptm_sites", {})
        phos_sites = len(ptm.get("phosphorylation", []))
        glyco_sites = len(ptm.get("glycosylation", []))

        if phos_sites > 10:
            if self.lang == Language.ZH:
                parts.append(f"检测到大量磷酸化位点（{phos_sites} 个），可能受到广泛的磷酸化调控")
            else:
                parts.append(
                    f"Numerous phosphorylation sites detected ({phos_sites}), may be extensively regulated by phosphorylation"
                )
        elif phos_sites > 0:
            parts.append(self.protein_i18n.get("ptm_sites", count=phos_sites))

        if glyco_sites > 0:
            if self.lang == Language.ZH:
                parts.append(f"包含 {glyco_sites} 个 N-糖基化位点，可能为糖蛋白")
            else:
                parts.append(f"Contains {glyco_sites} N-glycosylation site(s), may be a glycoprotein")

        # 连接并返回
        separator = self.protein_i18n.get("separator")
        terminator = self.protein_i18n.get("terminator")
        return separator.join(parts) + terminator


def get_language(lang_code: str) -> Language:
    """
    解析语言代码

    Args:
        lang_code: 语言代码字符串

    Returns:
        Language 枚举
    """
    lang_code = lang_code.lower().strip()

    # 支持多种输入格式
    if lang_code in ("zh", "zh-cn", "zh_cn", "chinese", "中文"):
        return Language.ZH

    # 默认英文
    return Language.EN
