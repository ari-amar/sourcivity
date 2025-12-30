// Dummy data for precision linear bearing search
// This replaces the LLM API calls with static data

export interface DummySearchResult {
  query: string;
  response: string;
  columns: string[];
}

export const DUMMY_SEARCH_DATA: Record<string, DummySearchResult> = {
  'precision linear bearing': {
    query: 'precision linear bearing',
    columns: ['Model', 'Bore Diameter', 'Dynamic Load Rating', 'Static Load Rating', 'Accuracy Class', 'Max Speed'],
    response: `| Model | Bore Diameter | Dynamic Load Rating | Static Load Rating | Accuracy Class | Max Speed |
| --- | --- | --- | --- | --- | --- |
| [THK SHS15LV](https://www.thk.com/us/products/linear_motion/linear_guides/shs_lv/)<br/>🇯🇵 OEM<br/>✓ 4.8★ | 15 mm | 16.2 kN | 24.6 kN | High (H) | 420 m/min |
| [Bosch Rexroth R1651 15](https://store.boschrexroth.com/en/us/p/ball-runner-block-carbon-steel-r165111320?srsltid=AfmBOopjr4JWJsSkQ9k8aCxWrV64OF-bFtBI5ZMOsACKEXKPoaXYloV5#downloads)<br/>🇩🇪 OEM<br/>✓ 4.7★ | 15 mm | 14.5 kN | 21.8 kN | Normal (N) | 300 m/min |
| [IKO LinearGuide LWH15](https://www.ikont.co.jp/eg/products/linear_guide/lwh/)<br/>🇯🇵 OEM<br/>✓ 4.6★ | 15 mm | 12.8 kN | 19.2 kN | High (H) | 350 m/min |
| [NSK NH15](https://www.nsk.com/products/linear-guides/nh/)<br/>🇯🇵 OEM<br/>✓ 4.5★ | 15 mm | 14.2 kN | 11.3 kN | High Precision (P5) | 300 m/min |
| [Rollon INA KGL15](https://www.rollon.com/en/linear-guides/miniature-linear-guides/kgl15)<br/>🇮🇹 OEM (INA)<br/>✓ 4.6★ | 15 mm | 13.7 kN | 20.5 kN | G3 | 320 m/min |`
  }
};

// Datasheet mapping for each product
export const DATASHEET_LINKS: Record<string, string> = {
  'THK SHS15LV': 'https://www.thk.com/download/catalog/pdf/lm_guide_ball_retainer_en.pdf',
  'Bosch Rexroth R1651 15': 'https://www.tuli.si/media/custom/upload/R1651_Rexroth.pdf',
  'IKO LinearGuide LWH15': 'https://www.ikont.co.jp/eg/data/pdf/lwh_e.pdf',
  'NSK NH15': 'https://www.nsk.com/content/dam/nsk/common/pdf/nh_e.pdf',
  'Rollon INA KGL15': 'https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/catalogues/ina_fag/downloads/l1_ina_linear_technology_1_en_us.pdf'
};

// Helper function to get datasheet link by part name
export function getDatasheetLink(partName: string): string | undefined {
  // partName should already be clean (e.g., "THK SHS15LV")
  return DATASHEET_LINKS[partName];
}
