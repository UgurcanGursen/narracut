import copy
import dataclasses
import gc
import hashlib
import inspect
import json
import weakref

import pytest

import engine.contracts.alignment_report as report_contracts
import engine.contracts.alignment_result as result_contracts
import engine.contracts.narration as narration_contracts
from engine.contracts import (
    canonicalize_temporal_raw_package,
    compile_caption_groups,
    load_repository_timing_origin_evidence,
    materialize_adapter_execution,
    materialize_alignment_request,
    materialize_alignment_result,
)
from engine.contracts.alignment_report import (
    ALIGNMENT_REPORT_FINDING_HASH_V1,
    ALIGNMENT_REPORT_FINDING_V1,
    ALIGNMENT_REPORT_HASH_V1,
    ALIGNMENT_REPORT_POLICY_V1,
    ALIGNMENT_REPORT_V1,
    AlignmentFindingScope,
    AlignmentFindingSeverity,
    AlignmentReport,
    AlignmentReportContractError,
    AlignmentReportFinding,
    AlignmentReportPolicy,
    AlignmentReportRejectionReason,
    AlignmentReportStatus,
    compile_alignment_report,
    load_alignment_report,
    serialize_alignment_report,
)
from tests.test_alignment_result import (
    PAYLOAD_BYTES, _canonical, _dependencies, _execution_value, _materialize,
    _rehash, _request_value, _result_value,
)
from tests.test_caption_groups import _compile as compile_groups


POLICY = AlignmentReportPolicy(
    ALIGNMENT_REPORT_POLICY_V1, 950_000, 900_000, 950_000, 900_000,
    250_000, 750_000,
)
AVAILABLE_HASH = "2921b750d2ab27860c634e4aaa4a87613744b8bce536a87770183176e59ba4b3"
AVAILABLE_ID = "alrep_2921b750d2ab27860c634e4aaa4a8761"
AVAILABLE_ENVELOPE_SHA = "606e62eaa9ffcef384525e8d437f63eb00049e98cc2c58e38adf78d61467b10b"
AVAILABLE_PROJECTION_BYTES = b'{"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":2,"evaluated_word_confidence_count":4,"findings":[{"alignment_report_finding_hash":"3fe0abeaeb8d265dcf503bfd3237eaa515d2e2c4b78ad690418e561c8020b81c","alignment_report_finding_id":"alrf_3fe0abeaeb8d265dcf503bfd3237eaa5","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":940000,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_49e85bb034c88ef36f26","word_ordinal":2},{"alignment_report_finding_hash":"e49d551993edaa3fed3167f580fc38f1e9d52602fd0922060ed368bf7c387765","alignment_report_finding_id":"alrf_e49d551993edaa3fed3167f580fc38f1","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":1,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_d81fe913754f8b49c296","word_ordinal":3},{"alignment_report_finding_hash":"db4e372581fddbc241fddac4108dd342be4926589bcf0e9164638aeccdeff460","alignment_report_finding_id":"alrf_db4e372581fddbc241fddac4108dd342","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","caption_group_ordinal":1,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":4,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"SEGMENT_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":2,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"CAPTION_GROUP","severity":"WARNING","start_word_ordinal":2,"threshold_millionths":950000,"word_id":null,"word_ordinal":null},{"alignment_report_finding_hash":"90219b749491c44b3ebe9e146ed2db3fe87329b83a747442316f12822bf5ad73","alignment_report_finding_id":"alrf_90219b749491c44b3ebe9e146ed2db3f","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"LOW_CONFIDENCE_RATIO_WARNING","observed_millionths":500000,"ordinal":3,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":250000,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":1,"low_confidence_word_count":2,"low_confidence_word_ratio_millionths":500000,"minimum_caption_group_confidence_millionths":920000,"minimum_word_confidence_millionths":920000,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"REVIEW_REQUIRED","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03","timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_source":"REPLAY_VERIFIED","warning_finding_count":4,"word_count":4}'
AVAILABLE_ENVELOPE_BYTES = b'{"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_report_hash":"2921b750d2ab27860c634e4aaa4a87613744b8bce536a87770183176e59ba4b3","alignment_report_id":"alrep_2921b750d2ab27860c634e4aaa4a8761","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":2,"evaluated_word_confidence_count":4,"findings":[{"alignment_report_finding_hash":"3fe0abeaeb8d265dcf503bfd3237eaa515d2e2c4b78ad690418e561c8020b81c","alignment_report_finding_id":"alrf_3fe0abeaeb8d265dcf503bfd3237eaa5","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":940000,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_49e85bb034c88ef36f26","word_ordinal":2},{"alignment_report_finding_hash":"e49d551993edaa3fed3167f580fc38f1e9d52602fd0922060ed368bf7c387765","alignment_report_finding_id":"alrf_e49d551993edaa3fed3167f580fc38f1","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":1,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_d81fe913754f8b49c296","word_ordinal":3},{"alignment_report_finding_hash":"db4e372581fddbc241fddac4108dd342be4926589bcf0e9164638aeccdeff460","alignment_report_finding_id":"alrf_db4e372581fddbc241fddac4108dd342","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","caption_group_ordinal":1,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":4,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"SEGMENT_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":2,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"CAPTION_GROUP","severity":"WARNING","start_word_ordinal":2,"threshold_millionths":950000,"word_id":null,"word_ordinal":null},{"alignment_report_finding_hash":"90219b749491c44b3ebe9e146ed2db3fe87329b83a747442316f12822bf5ad73","alignment_report_finding_id":"alrf_90219b749491c44b3ebe9e146ed2db3f","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"LOW_CONFIDENCE_RATIO_WARNING","observed_millionths":500000,"ordinal":3,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":250000,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":1,"low_confidence_word_count":2,"low_confidence_word_ratio_millionths":500000,"minimum_caption_group_confidence_millionths":920000,"minimum_word_confidence_millionths":920000,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"REVIEW_REQUIRED","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03","timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_source":"REPLAY_VERIFIED","warning_finding_count":4,"word_count":4}'
UNAVAILABLE_PROJECTION_BYTES = b'{"adapter_execution_hash":"752dfa887cc4a7113694edf6ea0ee9d0bad5309d568f8ac64a3b641b4bacf748","adapter_execution_id":"aex_752dfa887cc4a7113694edf6ea0ee9d0","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"221f2b935363a3d8d2558758f51e244e1dc0a01432b72271ba31e2346d70f8ce","alignment_request_id":"arq_221f2b935363a3d8d2558758f51e244e","alignment_result_hash":"37fe217ac2c4f77467235bb12536e26aa783ef4b5d1dea086b8661484b971c5e","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"c15e3afcaa73e13ca40d447edfa37f49f58fc997d5999ba8db7f6a87953d0945","caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","confidence_availability":"UNAVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[{"alignment_report_finding_hash":"a663b34ca488743c2c562f9199f48de3e0363767f2c8d3ac306491d3c521c887","alignment_report_finding_id":"alrf_a663b34ca488743c2c562f9199f48de3","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"CONFIDENCE_UNAVAILABLE","observed_millionths":null,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":null,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_UNAVAILABLE","temporal_raw_package_hash":"sha256:6652c8f26f43feaa0286db948724edde455877aadff5a762a791cc2cbee8ab76","timing_origin_evidence_hash":"9bbb6108462700a035fbf60c8d7233b720302a46e6b8a8a0389b3dcde71c60de","timing_origin_evidence_id":"toe_9bbb6108462700a035fbf60c8d7233b7","timing_source":"REPLAY_VERIFIED","warning_finding_count":1,"word_count":4}'
UNAVAILABLE_ENVELOPE_BYTES = b'{"adapter_execution_hash":"752dfa887cc4a7113694edf6ea0ee9d0bad5309d568f8ac64a3b641b4bacf748","adapter_execution_id":"aex_752dfa887cc4a7113694edf6ea0ee9d0","alignment_report_hash":"1b52419d9c9e41dbfc7a6f4517d5909e0dd1ad330729b9c83f06a6a2f384acaf","alignment_report_id":"alrep_1b52419d9c9e41dbfc7a6f4517d5909e","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"221f2b935363a3d8d2558758f51e244e1dc0a01432b72271ba31e2346d70f8ce","alignment_request_id":"arq_221f2b935363a3d8d2558758f51e244e","alignment_result_hash":"37fe217ac2c4f77467235bb12536e26aa783ef4b5d1dea086b8661484b971c5e","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"c15e3afcaa73e13ca40d447edfa37f49f58fc997d5999ba8db7f6a87953d0945","caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","confidence_availability":"UNAVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[{"alignment_report_finding_hash":"a663b34ca488743c2c562f9199f48de3e0363767f2c8d3ac306491d3c521c887","alignment_report_finding_id":"alrf_a663b34ca488743c2c562f9199f48de3","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"CONFIDENCE_UNAVAILABLE","observed_millionths":null,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":null,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_UNAVAILABLE","temporal_raw_package_hash":"sha256:6652c8f26f43feaa0286db948724edde455877aadff5a762a791cc2cbee8ab76","timing_origin_evidence_hash":"9bbb6108462700a035fbf60c8d7233b720302a46e6b8a8a0389b3dcde71c60de","timing_origin_evidence_id":"toe_9bbb6108462700a035fbf60c8d7233b7","timing_source":"REPLAY_VERIFIED","warning_finding_count":1,"word_count":4}'
NOT_APPLICABLE_PROJECTION_BYTES = b'{"adapter_execution_hash":"5dd490c52cbc151cfd809e503709772f08e9d3c613ca6c86ca23a4606e020ba5","adapter_execution_id":"aex_5dd490c52cbc151cfd809e503709772f","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"e83198f3b09b4a2d165dacf873ba796cd21f691403e71934f98db6dc19e7dee1","alignment_request_id":"arq_e83198f3b09b4a2d165dacf873ba796c","alignment_result_hash":"00c3cd8b81ae25698e01cbd29716918223e327840cf9af5d3036dbc05b38b16c","alignment_result_id":"alr_00c3cd8b81ae25698e01cbd297169182","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"0aabeea64c7fc2733d9e678f6b3704ab20d95a7cb6a697afff4f15e2b3684322","caption_groups_id":"cgs_0aabeea64c7fc2733d9e678f6b3704ab","confidence_availability":"NOT_APPLICABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_NOT_APPLICABLE","temporal_raw_package_hash":"sha256:6b2859827c7bede701b4a4d0f90fb45a4727345d8b4ce1fb60247ec6d9f3ea54","timing_origin_evidence_hash":"ce6210ed324917ab2d9c8c2514b6b77f327a54feab01a765ce063e13092c642b","timing_origin_evidence_id":"toe_ce6210ed324917ab2d9c8c2514b6b77f","timing_source":"REPLAY_VERIFIED","warning_finding_count":0,"word_count":4}'
NOT_APPLICABLE_ENVELOPE_BYTES = b'{"adapter_execution_hash":"5dd490c52cbc151cfd809e503709772f08e9d3c613ca6c86ca23a4606e020ba5","adapter_execution_id":"aex_5dd490c52cbc151cfd809e503709772f","alignment_report_hash":"0d777cf83342fc7e399fe98eaa5007329c7960a133c58bf9eb0674e4a55ae470","alignment_report_id":"alrep_0d777cf83342fc7e399fe98eaa500732","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"e83198f3b09b4a2d165dacf873ba796cd21f691403e71934f98db6dc19e7dee1","alignment_request_id":"arq_e83198f3b09b4a2d165dacf873ba796c","alignment_result_hash":"00c3cd8b81ae25698e01cbd29716918223e327840cf9af5d3036dbc05b38b16c","alignment_result_id":"alr_00c3cd8b81ae25698e01cbd297169182","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"0aabeea64c7fc2733d9e678f6b3704ab20d95a7cb6a697afff4f15e2b3684322","caption_groups_id":"cgs_0aabeea64c7fc2733d9e678f6b3704ab","confidence_availability":"NOT_APPLICABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_NOT_APPLICABLE","temporal_raw_package_hash":"sha256:6b2859827c7bede701b4a4d0f90fb45a4727345d8b4ce1fb60247ec6d9f3ea54","timing_origin_evidence_hash":"ce6210ed324917ab2d9c8c2514b6b77f327a54feab01a765ce063e13092c642b","timing_origin_evidence_id":"toe_ce6210ed324917ab2d9c8c2514b6b77f","timing_source":"REPLAY_VERIFIED","warning_finding_count":0,"word_count":4}'


@pytest.fixture(scope="module")
def fx():
    deps = _dependencies()
    result = _materialize(_result_value(deps), deps)
    groups = compile_groups((deps[1], deps[2], result))
    return deps[1], deps[2], result, groups


def _compile(fx, policy=POLICY):
    document, revision, result, groups = fx
    return compile_alignment_report(
        narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, policy=policy,
    )


def _load(fx, source, policy=POLICY):
    document, revision, result, groups = fx
    return load_alignment_report(
        source, narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, policy=policy,
    )


def _assert_error(error, pointer, reason, issue=None):
    value = error.value
    assert value.pointer == pointer
    assert value.reason is reason
    assert value.issue_code == issue
    assert str(value) == f"Alignment report rejected: {reason.value}"


def _literal_canonical(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")


@pytest.mark.parametrize(
    "projection,envelope,projection_length,report_hash,report_id,envelope_sha",
    [
        (
            AVAILABLE_PROJECTION_BYTES, AVAILABLE_ENVELOPE_BYTES, 5610,
            "2921b750d2ab27860c634e4aaa4a87613744b8bce536a87770183176e59ba4b3",
            "alrep_2921b750d2ab27860c634e4aaa4a8761",
            "606e62eaa9ffcef384525e8d437f63eb00049e98cc2c58e38adf78d61467b10b",
        ),
        (
            UNAVAILABLE_PROJECTION_BYTES, UNAVAILABLE_ENVELOPE_BYTES, 3105,
            "1b52419d9c9e41dbfc7a6f4517d5909e0dd1ad330729b9c83f06a6a2f384acaf",
            "alrep_1b52419d9c9e41dbfc7a6f4517d5909e",
            "64b9facf58d6790596c85c299714ac4f8b7b52c308d1ad532548ec8c369d1c33",
        ),
        (
            NOT_APPLICABLE_PROJECTION_BYTES, NOT_APPLICABLE_ENVELOPE_BYTES, 2313,
            "0d777cf83342fc7e399fe98eaa5007329c7960a133c58bf9eb0674e4a55ae470",
            "alrep_0d777cf83342fc7e399fe98eaa500732",
            "b894b07465ba77d1111db6fe84b3e254766480deefb85b7a242a1f05462e27de",
        ),
    ],
)
def test_three_state_complete_literal_projection_and_envelope_oracles(
    projection, envelope, projection_length, report_hash, report_id, envelope_sha,
):
    assert len(projection) == projection_length
    assert hashlib.sha256(projection).hexdigest() == report_hash
    assert len(envelope) == projection_length + 154
    assert hashlib.sha256(envelope).hexdigest() == envelope_sha
    projection_value = json.loads(projection)
    envelope_value = json.loads(envelope)
    assert _literal_canonical(projection_value) == projection
    assert _literal_canonical(envelope_value) == envelope
    assert envelope_value["alignment_report_hash"] == report_hash
    assert envelope_value["alignment_report_id"] == report_id
    assert {
        key: value for key, value in envelope_value.items()
        if key not in {"alignment_report_id", "alignment_report_hash"}
    } == projection_value
    policy_bytes = _literal_canonical(projection_value["alignment_report_policy"])
    assert projection_value["alignment_report_policy_snapshot_hash"] == (
        "sha256:" + hashlib.sha256(policy_bytes).hexdigest()
    )
    for finding in projection_value["findings"]:
        finding_projection = {
            key: value for key, value in finding.items()
            if key not in {
                "alignment_report_finding_id", "alignment_report_finding_hash",
            }
        }
        digest = hashlib.sha256(_literal_canonical(finding_projection)).hexdigest()
        assert finding["alignment_report_finding_hash"] == digest
        assert finding["alignment_report_finding_id"] == "alrf_" + digest[:32]


def test_exact_public_surface_models_and_signatures():
    assert ALIGNMENT_REPORT_V1 == "ALIGNMENT-REPORT-V1"
    assert ALIGNMENT_REPORT_HASH_V1 == "ALIGNMENT-REPORT-HASH-V1"
    assert ALIGNMENT_REPORT_FINDING_V1 == "ALIGNMENT-REPORT-FINDING-V1"
    assert ALIGNMENT_REPORT_FINDING_HASH_V1 == "ALIGNMENT-REPORT-FINDING-HASH-V1"
    assert ALIGNMENT_REPORT_POLICY_V1 == "ALIGNMENT-REPORT-POLICY-V1"
    assert [item.value for item in AlignmentReportStatus] == [
        "PASS", "REVIEW_REQUIRED", "BLOCKED", "CONFIDENCE_UNAVAILABLE",
        "CONFIDENCE_NOT_APPLICABLE",
    ]
    assert [item.value for item in AlignmentFindingSeverity] == ["WARNING", "BLOCKER"]
    assert [item.value for item in AlignmentFindingScope] == ["WORD", "CAPTION_GROUP", "REPORT"]
    assert [item.value for item in AlignmentReportRejectionReason] == [
        "STRUCTURE_INVALID", "UNSUPPORTED_VALUE", "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID", "POLICY_INVALID", "CONFIDENCE_INVALID",
        "FINDING_INVALID", "NON_CANONICAL_SERIALIZATION", "IDENTITY_MISMATCH",
        "CONTENT_DRIFT", "NOT_MATERIALIZED",
    ]
    assert [field.name for field in dataclasses.fields(AlignmentReportPolicy)] == [
        "policy_version", "individual_warning_below_millionths",
        "individual_blocker_below_millionths", "caption_group_warning_below_millionths",
        "caption_group_blocker_below_millionths",
        "low_confidence_ratio_warning_at_or_above_millionths",
        "low_confidence_ratio_blocker_at_or_above_millionths",
    ]
    assert len(dataclasses.fields(AlignmentReportFinding)) == 19
    assert len(dataclasses.fields(AlignmentReport)) == 38
    assert list(inspect.signature(compile_alignment_report).parameters) == [
        "narration_document", "narration_revision", "alignment_result",
        "caption_groups", "policy",
    ]
    assert list(inspect.signature(load_alignment_report).parameters) == [
        "source", "narration_document", "narration_revision", "alignment_result",
        "caption_groups", "policy",
    ]
    assert list(inspect.signature(serialize_alignment_report).parameters) == ["report"]


def test_available_golden_metrics_findings_identity_and_round_trip(fx):
    report = _compile(fx)
    envelope = serialize_alignment_report(report)
    assert report.alignment_report_hash == AVAILABLE_HASH
    assert report.alignment_report_id == AVAILABLE_ID
    assert len(envelope) == 5764
    assert hashlib.sha256(envelope).hexdigest() == AVAILABLE_ENVELOPE_SHA
    assert envelope == AVAILABLE_ENVELOPE_BYTES
    assert report.status is AlignmentReportStatus.REVIEW_REQUIRED
    assert (report.word_count, report.caption_group_count) == (4, 2)
    assert (report.evaluated_word_confidence_count, report.evaluated_caption_group_confidence_count) == (4, 2)
    assert (report.minimum_word_confidence_millionths, report.minimum_caption_group_confidence_millionths) == (920_000, 920_000)
    assert (report.low_confidence_word_count, report.low_confidence_caption_group_count, report.low_confidence_word_ratio_millionths) == (2, 1, 500_000)
    assert (report.warning_finding_count, report.blocker_finding_count) == (4, 0)
    assert [item.issue_code for item in report.findings] == [
        "INDIVIDUAL_CONFIDENCE_WARNING", "INDIVIDUAL_CONFIDENCE_WARNING",
        "SEGMENT_CONFIDENCE_WARNING", "LOW_CONFIDENCE_RATIO_WARNING",
    ]
    assert [item.ordinal for item in report.findings] == list(range(4))
    document, revision, result, groups = fx
    loaded = load_alignment_report(
        envelope, narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, policy=POLICY,
    )
    assert serialize_alignment_report(loaded) == envelope


@pytest.mark.parametrize(
    "policy",
    [
        None,
        dataclasses.replace(POLICY, policy_version="OTHER"),
        dataclasses.replace(POLICY, individual_warning_below_millionths=True),
        dataclasses.replace(POLICY, individual_warning_below_millionths=1_000_001),
        dataclasses.replace(POLICY, individual_blocker_below_millionths=950_000),
        dataclasses.replace(POLICY, caption_group_blocker_below_millionths=950_000),
        dataclasses.replace(POLICY, low_confidence_ratio_warning_at_or_above_millionths=750_000),
    ],
)
def test_policy_is_explicit_closed_and_ordered(fx, policy):
    with pytest.raises(AlignmentReportContractError) as error:
        _compile(fx, policy)
    assert error.value.reason is AlignmentReportRejectionReason.POLICY_INVALID


def test_threshold_equality_blocker_suppression_and_exact_ratio_gate(fx):
    document, revision, result, groups = fx
    # Internal derivation is isolated here to exercise the pure threshold compiler;
    # compile-path genuineness is covered separately.
    policy = AlignmentReportPolicy(
        ALIGNMENT_REPORT_POLICY_V1, 940_001, 920_001, 920_001, 900_000,
        500_000, 750_000,
    )
    owned, digest = report_contracts._validate_policy(policy)
    report = report_contracts._derive(document, revision, result, groups, owned, digest)
    assert report.findings[0].observed_millionths == 940_000
    assert report.findings[0].severity is AlignmentFindingSeverity.WARNING
    assert report.findings[1].observed_millionths == 920_000
    assert report.findings[1].severity is AlignmentFindingSeverity.BLOCKER
    assert report.findings[-1].issue_code == "LOW_CONFIDENCE_RATIO_WARNING"
    assert report.findings[-1].observed_millionths == 500_000
    assert report.status is AlignmentReportStatus.BLOCKED
    # Equality is clear for below-threshold gates.
    equality = dataclasses.replace(POLICY, individual_blocker_below_millionths=920_000)
    owned, digest = report_contracts._validate_policy(equality)
    report = report_contracts._derive(document, revision, result, groups, owned, digest)
    word_three = [item for item in report.findings if item.word_ordinal == 3][0]
    assert word_three.severity is AlignmentFindingSeverity.WARNING


def test_pass_blocked_and_ratio_adjacent_boundary_states(fx):
    pass_policy = AlignmentReportPolicy(
        ALIGNMENT_REPORT_POLICY_V1, 920_000, 0, 920_000, 0, 1, 2,
    )
    passed = _compile(fx, pass_policy)
    assert passed.status is AlignmentReportStatus.PASS
    assert passed.findings == ()
    assert (passed.warning_finding_count, passed.blocker_finding_count) == (0, 0)

    blocked_policy = AlignmentReportPolicy(
        ALIGNMENT_REPORT_POLICY_V1, 950_000, 940_001, 950_000, 920_001,
        0, 500_000,
    )
    blocked = _compile(fx, blocked_policy)
    assert blocked.status is AlignmentReportStatus.BLOCKED
    assert blocked.blocker_finding_count == 4
    assert [item.issue_code for item in blocked.findings] == [
        "INDIVIDUAL_CONFIDENCE_BLOCKER", "INDIVIDUAL_CONFIDENCE_BLOCKER",
        "SEGMENT_CONFIDENCE_BLOCKER", "LOW_CONFIDENCE_RATIO_BLOCKER",
    ]
    assert all(item.severity is AlignmentFindingSeverity.BLOCKER for item in blocked.findings)

    at_ratio = dataclasses.replace(
        POLICY, low_confidence_ratio_warning_at_or_above_millionths=500_000,
    )
    above_ratio = dataclasses.replace(
        POLICY, low_confidence_ratio_warning_at_or_above_millionths=500_001,
    )
    assert _compile(fx, at_ratio).findings[-1].issue_code == "LOW_CONFIDENCE_RATIO_WARNING"
    assert all(
        item.issue_code != "LOW_CONFIDENCE_RATIO_WARNING"
        for item in _compile(fx, above_ratio).findings
    )


def test_noninteger_ratio_uses_exact_adjacent_cross_multiplication_boundary(fx):
    document, revision, result, groups = fx
    three_word_result = dataclasses.replace(result, word_timings=result.word_timings[:3])
    one_group = dataclasses.replace(groups, caption_groups=groups.caption_groups[:1])

    def derive(ratio_warning):
        policy = AlignmentReportPolicy(
            ALIGNMENT_REPORT_POLICY_V1, 950_000, 0, 950_000, 0,
            ratio_warning, 1_000_000,
        )
        owned, policy_hash = report_contracts._validate_policy(policy)
        return report_contracts._derive(
            document, revision, three_word_result, one_group, owned, policy_hash,
        )

    at_boundary = derive(333_333)
    above_boundary = derive(333_334)
    assert at_boundary.low_confidence_word_count == 1
    assert at_boundary.evaluated_word_confidence_count == 3
    assert at_boundary.low_confidence_word_ratio_millionths == 333_333
    assert 1 * 1_000_000 >= 333_333 * 3
    assert 1 * 1_000_000 < 333_334 * 3
    assert at_boundary.findings[-1].issue_code == "LOW_CONFIDENCE_RATIO_WARNING"
    assert all(
        item.issue_code != "LOW_CONFIDENCE_RATIO_WARNING"
        for item in above_boundary.findings
    )


def test_available_finding_target_and_metric_null_matrix_is_closed(fx):
    report = _compile(fx)
    for finding in report.findings:
        assert finding.observed_millionths is not None
        assert finding.threshold_millionths is not None
        if finding.scope is AlignmentFindingScope.WORD:
            assert finding.word_ordinal is not None and finding.word_id is not None
            assert finding.caption_group_ordinal is None and finding.caption_group_id is None
            assert finding.start_word_ordinal is None and finding.end_exclusive_word_ordinal is None
        elif finding.scope is AlignmentFindingScope.CAPTION_GROUP:
            assert finding.word_ordinal is None and finding.word_id is None
            assert finding.caption_group_ordinal is not None and finding.caption_group_id is not None
            assert finding.start_word_ordinal is not None and finding.end_exclusive_word_ordinal is not None
        else:
            assert finding.scope is AlignmentFindingScope.REPORT
            assert finding.word_ordinal is None and finding.word_id is None
            assert finding.caption_group_ordinal is None and finding.caption_group_id is None
            assert finding.start_word_ordinal is None and finding.end_exclusive_word_ordinal is None


def test_dependency_copies_and_current_content_drift_fail_closed(fx):
    document, revision, result, groups = fx
    with pytest.raises(TypeError):
        compile_alignment_report(
            narration_document=dataclasses.replace(document), narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    with pytest.raises(TypeError):
        compile_alignment_report(
            narration_document=document, narration_revision=revision,
            alignment_result=dataclasses.replace(result), caption_groups=groups, policy=POLICY,
        )
    original = result.alignment_result_hash
    try:
        object.__setattr__(result, "alignment_result_hash", "0" * 64)
        with pytest.raises(AlignmentReportContractError) as error:
            _compile(fx)
        _assert_error(error, "/alignment_result", AlignmentReportRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH")
    finally:
        object.__setattr__(result, "alignment_result_hash", original)


def test_all_dependency_exact_types_and_current_content_are_required(fx):
    document, revision, result, groups = fx
    bad_values = [
        ("narration_document", dataclasses.replace(document)),
        ("narration_revision", dataclasses.replace(revision)),
        ("alignment_result", dataclasses.replace(result)),
        ("caption_groups", dataclasses.replace(groups)),
    ]
    for field, forged in bad_values:
        kwargs = {
            "narration_document": document, "narration_revision": revision,
            "alignment_result": result, "caption_groups": groups, "policy": POLICY,
        }
        kwargs[field] = forged
        with pytest.raises(TypeError):
            compile_alignment_report(**kwargs)

    drift_cases = [
        (document, "current_revision_id", "/narration_document", True),
        (revision, "revision_hash", "/narration_revision", True),
        (result, "alignment_result_hash", "/alignment_result", False),
        (groups, "caption_groups_hash", "/caption_groups", False),
    ]
    for dependency, field, pointer, narration in drift_cases:
        original = getattr(dependency, field)
        replacement = "sha256:" + "0" * 64 if original.startswith("sha256:") else "0" * len(original)
        try:
            object.__setattr__(dependency, field, replacement)
            with pytest.raises(AlignmentReportContractError) as error:
                _compile(fx)
            _assert_error(
                error, pointer, AlignmentReportRejectionReason.DEPENDENCY_CONTENT_DRIFT,
                "ALIGNMENT_REQUEST_IDENTITY_MISMATCH" if narration else "REPLAY_HASH_MISMATCH",
            )
        finally:
            object.__setattr__(dependency, field, original)


def test_dependency_cross_binding_inventory_and_confidence_branches(fx, monkeypatch):
    document, revision, result, groups = fx

    forged_document = dataclasses.replace(document, current_revision_id="narrev_other")
    monkeypatch.setattr(report_contracts, "_has_materialized_narration_document_identity", lambda value: True)
    monkeypatch.setattr(report_contracts, "_is_materialized_narration_document", lambda value: True)
    with pytest.raises(AlignmentReportContractError) as error:
        compile_alignment_report(
            narration_document=forged_document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(
        error, "/narration_revision",
        AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )

    monkeypatch.setattr(report_contracts, "serialize_alignment_result", lambda value: b"accepted")
    forged_result = dataclasses.replace(result, project_id="prj_other")
    with pytest.raises(AlignmentReportContractError) as error:
        compile_alignment_report(
            narration_document=document, narration_revision=revision,
            alignment_result=forged_result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(
        error, "/alignment_result",
        AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )

    forged_result = dataclasses.replace(result, word_timings=result.word_timings[:-1])
    with pytest.raises(AlignmentReportContractError) as error:
        compile_alignment_report(
            narration_document=document, narration_revision=revision,
            alignment_result=forged_result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(
        error, "/alignment_result",
        AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )

    monkeypatch.setattr(report_contracts, "serialize_caption_groups", lambda value: b"accepted")
    forged_groups = dataclasses.replace(groups, project_id="prj_other")
    with pytest.raises(AlignmentReportContractError) as error:
        compile_alignment_report(
            narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=forged_groups, policy=POLICY,
        )
    _assert_error(
        error, "/caption_groups",
        AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )

    other_availability = next(
        item for item in result_contracts.ConfidenceAvailability
        if item is not result.confidence_availability
    )
    forged_groups = dataclasses.replace(groups, confidence_availability=other_availability)
    with pytest.raises(AlignmentReportContractError) as error:
        compile_alignment_report(
            narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=forged_groups, policy=POLICY,
        )
    _assert_error(
        error, "/caption_groups", AlignmentReportRejectionReason.CONFIDENCE_INVALID,
        "ADAPTER_PRECISION_OVERSTATED",
    )

    first_group = dataclasses.replace(groups.caption_groups[0], end_exclusive_word_ordinal=1)
    forged_groups = dataclasses.replace(
        groups, caption_groups=(first_group, *groups.caption_groups[1:]),
    )
    with pytest.raises(AlignmentReportContractError) as error:
        compile_alignment_report(
            narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=forged_groups, policy=POLICY,
        )
    _assert_error(
        error, "/caption_groups",
        AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


def test_loader_rejects_noncanonical_shape_identity_and_semantic_changes(fx):
    report = _compile(fx)
    envelope = serialize_alignment_report(report)
    document, revision, result, groups = fx
    load = lambda source: load_alignment_report(
        source, narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, policy=POLICY,
    )
    with pytest.raises(AlignmentReportContractError) as error:
        load(envelope + b"\n")
    _assert_error(error, "/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION)
    value = json.loads(envelope)
    value["extra"] = 1
    with pytest.raises(AlignmentReportContractError) as error:
        load(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())
    _assert_error(error, "/", AlignmentReportRejectionReason.STRUCTURE_INVALID)
    value = json.loads(envelope)
    value["findings"][0]["severity"] = "BLOCKER"
    with pytest.raises(AlignmentReportContractError) as error:
        load(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())
    _assert_error(error, "/findings/0", AlignmentReportRejectionReason.FINDING_INVALID, "INDIVIDUAL_CONFIDENCE_WARNING")
    value = json.loads(envelope)
    value["alignment_report_hash"] = "0" * 64
    with pytest.raises(AlignmentReportContractError) as error:
        load(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())
    _assert_error(error, "/", AlignmentReportRejectionReason.IDENTITY_MISMATCH)


@pytest.mark.parametrize(
    "source_factory",
    [
        lambda envelope: b'{' + b'"duplicate":1,"duplicate":2}',
        lambda envelope: b"\xff",
        lambda envelope: b"\xef\xbb\xbf" + envelope,
        lambda envelope: envelope + b"\n",
        lambda envelope: envelope.replace(b'"blocker_finding_count":0', b'"blocker_finding_count":0.0', 1),
        lambda envelope: envelope.replace(b'"blocker_finding_count":0', b'"blocker_finding_count":-0', 1),
        lambda envelope: json.dumps(
            {key: value for key, value in reversed(tuple(json.loads(envelope).items()))},
            ensure_ascii=False, separators=(",", ":"), sort_keys=False,
        ).encode("utf-8"),
        lambda envelope: _literal_canonical({**json.loads(envelope), "project_id": "e\u0301"}),
    ],
)
def test_loader_rejects_every_forbidden_wire_form_as_noncanonical(fx, source_factory):
    source = source_factory(AVAILABLE_ENVELOPE_BYTES)
    assert source != AVAILABLE_ENVELOPE_BYTES
    with pytest.raises(AlignmentReportContractError) as error:
        _load(fx, source)
    _assert_error(
        error, "/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION,
    )


def test_loader_requires_exact_builtin_bytes(fx):
    class BytesSubclass(bytes):
        pass

    with pytest.raises(AlignmentReportContractError) as error:
        _load(fx, BytesSubclass(AVAILABLE_ENVELOPE_BYTES))
    _assert_error(error, "/", AlignmentReportRejectionReason.STRUCTURE_INVALID)


@pytest.mark.parametrize(
    "mutation,pointer,reason",
    [
        (lambda root: root.__setitem__("unknown", 1), "/", AlignmentReportRejectionReason.STRUCTURE_INVALID),
        (lambda root: root.pop("project_id"), "/", AlignmentReportRejectionReason.STRUCTURE_INVALID),
        (lambda root: root.__setitem__("alignment_report_policy", []), "/alignment_report_policy", AlignmentReportRejectionReason.POLICY_INVALID),
        (lambda root: root["alignment_report_policy"].__setitem__("unknown", 1), "/alignment_report_policy", AlignmentReportRejectionReason.POLICY_INVALID),
        (lambda root: root["alignment_report_policy"].pop("policy_version"), "/alignment_report_policy", AlignmentReportRejectionReason.POLICY_INVALID),
        (lambda root: root.__setitem__("findings", {}), "/findings", AlignmentReportRejectionReason.STRUCTURE_INVALID),
        (lambda root: root["findings"][0].__setitem__("unknown", 1), "/findings/0", AlignmentReportRejectionReason.STRUCTURE_INVALID),
        (lambda root: root["findings"][0].pop("word_id"), "/findings/0", AlignmentReportRejectionReason.STRUCTURE_INVALID),
        (lambda root: root["findings"].pop(), "/findings", AlignmentReportRejectionReason.STRUCTURE_INVALID),
    ],
)
def test_loader_exact_shape_unknown_missing_and_count_oracles(fx, mutation, pointer, reason):
    wire = json.loads(AVAILABLE_ENVELOPE_BYTES)
    mutation(wire)
    with pytest.raises(AlignmentReportContractError) as error:
        _load(fx, _literal_canonical(wire))
    _assert_error(error, pointer, reason)


@pytest.mark.parametrize(
    "target,field",
    [
        ("finding", "alignment_report_finding_hash"),
        ("finding", "alignment_report_finding_id"),
        ("root", "alignment_report_hash"),
        ("root", "alignment_report_id"),
    ],
)
def test_loader_checks_finding_and_report_hash_then_id(fx, target, field):
    wire = json.loads(AVAILABLE_ENVELOPE_BYTES)
    container = wire["findings"][0] if target == "finding" else wire
    container[field] = "0" * (64 if field.endswith("hash") else len(container[field]))
    with pytest.raises(AlignmentReportContractError) as error:
        _load(fx, _literal_canonical(wire))
    _assert_error(
        error, "/findings/0" if target == "finding" else "/",
        AlignmentReportRejectionReason.IDENTITY_MISMATCH,
    )


def test_loader_semantics_precede_identity_and_sanitizes_multifault(fx):
    wire = json.loads(AVAILABLE_ENVELOPE_BYTES)
    wire["findings"][0]["severity"] = "BLOCKER"
    wire["findings"][0]["alignment_report_finding_hash"] = "0" * 64
    wire["findings"][0]["alignment_report_finding_id"] = "alrf_" + "0" * 32
    wire["alignment_report_hash"] = "0" * 64
    wire["alignment_report_id"] = "alrep_" + "0" * 32
    with pytest.raises(AlignmentReportContractError) as error:
        _load(fx, _literal_canonical(wire))
    _assert_error(
        error, "/findings/0", AlignmentReportRejectionReason.FINDING_INVALID,
        "INDIVIDUAL_CONFIDENCE_WARNING",
    )

    wire = json.loads(AVAILABLE_ENVELOPE_BYTES)
    wire.pop("project_id")
    wire["attacker-secret"] = "attacker-secret"
    with pytest.raises(AlignmentReportContractError) as error:
        _load(fx, _literal_canonical(wire))
    _assert_error(error, "/", AlignmentReportRejectionReason.STRUCTURE_INVALID)
    assert "attacker-secret" not in str(error.value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("word_count", True),
        ("word_count", -1),
        ("word_count", 2**32),
        ("minimum_word_confidence_millionths", 1_000_001),
        ("warning_finding_count", False),
    ],
)
def test_loader_rejects_root_scalar_type_and_range_before_semantics(fx, field, value):
    report = _compile(fx)
    document, revision, result, groups = fx
    wire = json.loads(serialize_alignment_report(report))
    wire[field] = value
    source = json.dumps(wire, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(AlignmentReportContractError) as error:
        load_alignment_report(
            source, narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(error, "/", AlignmentReportRejectionReason.STRUCTURE_INVALID)


@pytest.mark.parametrize(
    "field,value,pointer,reason,issue",
    [
        ("timing_source", "UNKNOWN", "/", AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        ("confidence_availability", "UNKNOWN", "/", AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        ("status", "UNKNOWN", "/", AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        ("confidence_availability", "UNAVAILABLE", "/alignment_result", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
        ("status", "PASS", "/alignment_result", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
        ("minimum_word_confidence_millionths", None, "/alignment_result", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
    ],
)
def test_loader_distinguishes_unknown_enums_from_valid_derived_mismatches(
    fx, field, value, pointer, reason, issue,
):
    report = _compile(fx)
    document, revision, result, groups = fx
    wire = json.loads(serialize_alignment_report(report))
    wire[field] = value
    source = json.dumps(wire, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(AlignmentReportContractError) as error:
        load_alignment_report(
            source, narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(error, pointer, reason, issue)


@pytest.mark.parametrize(
    "field,value,pointer",
    [
        ("project_id", "prj_other", "/narration_document"),
        ("narration_revision_hash", "sha256:" + "0" * 64, "/narration_revision"),
        ("alignment_result_hash", "0" * 64, "/alignment_result"),
        ("caption_groups_hash", "0" * 64, "/caption_groups"),
        ("word_count", 3, "/alignment_result"),
        ("caption_group_count", 1, "/caption_groups"),
    ],
)
def test_loader_root_declaration_and_metric_drift_use_dependency_pointer(
    fx, field, value, pointer,
):
    report = _compile(fx)
    document, revision, result, groups = fx
    wire = json.loads(serialize_alignment_report(report))
    wire[field] = value
    source = json.dumps(wire, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(AlignmentReportContractError) as error:
        load_alignment_report(
            source, narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(
        error, pointer, AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


def test_loader_routes_embedded_policy_drift_to_policy_oracle(fx):
    report = _compile(fx)
    document, revision, result, groups = fx
    wire = json.loads(serialize_alignment_report(report))
    wire["alignment_report_policy"]["individual_warning_below_millionths"] -= 1
    source = json.dumps(wire, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(AlignmentReportContractError) as error:
        load_alignment_report(
            source, narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(
        error, "/alignment_report_policy",
        AlignmentReportRejectionReason.POLICY_INVALID,
    )


@pytest.mark.parametrize("field,value", [("ordinal", True), ("ordinal", -1), ("observed_millionths", 1_000_001)])
def test_loader_rejects_finding_scalar_type_and_range(fx, field, value):
    report = _compile(fx)
    document, revision, result, groups = fx
    wire = json.loads(serialize_alignment_report(report))
    wire["findings"][0][field] = value
    source = json.dumps(wire, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(AlignmentReportContractError) as error:
        load_alignment_report(
            source, narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(error, "/findings/0", AlignmentReportRejectionReason.STRUCTURE_INVALID)


@pytest.mark.parametrize(
    "field,value,reason,issue",
    [
        ("issue_code", "UNKNOWN", AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        ("severity", "UNKNOWN", AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        ("scope", "UNKNOWN", AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        ("issue_code", "SEGMENT_CONFIDENCE_WARNING", AlignmentReportRejectionReason.FINDING_INVALID, "INDIVIDUAL_CONFIDENCE_WARNING"),
        ("severity", "BLOCKER", AlignmentReportRejectionReason.FINDING_INVALID, "INDIVIDUAL_CONFIDENCE_WARNING"),
        ("scope", "REPORT", AlignmentReportRejectionReason.FINDING_INVALID, "INDIVIDUAL_CONFIDENCE_WARNING"),
        ("word_ordinal", None, AlignmentReportRejectionReason.FINDING_INVALID, "INDIVIDUAL_CONFIDENCE_WARNING"),
    ],
)
def test_loader_validates_finding_enums_and_exact_null_matrix(
    fx, field, value, reason, issue,
):
    report = _compile(fx)
    document, revision, result, groups = fx
    wire = json.loads(serialize_alignment_report(report))
    wire["findings"][0][field] = value
    source = json.dumps(wire, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(AlignmentReportContractError) as error:
        load_alignment_report(
            source, narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    _assert_error(error, "/findings/0", reason, issue)


def test_serialization_rejects_copy_mutation_and_nested_replacement(fx):
    report = _compile(fx)
    with pytest.raises(AlignmentReportContractError) as error:
        serialize_alignment_report(dataclasses.replace(report))
    _assert_error(error, "/", AlignmentReportRejectionReason.NOT_MATERIALIZED)
    original = report.alignment_report_hash
    try:
        object.__setattr__(report, "alignment_report_hash", "0" * 64)
        with pytest.raises(AlignmentReportContractError) as error:
            serialize_alignment_report(report)
        _assert_error(error, "/", AlignmentReportRejectionReason.CONTENT_DRIFT)
    finally:
        object.__setattr__(report, "alignment_report_hash", original)
    original_policy = report.alignment_report_policy
    try:
        object.__setattr__(report, "alignment_report_policy", dataclasses.replace(original_policy))
        with pytest.raises(AlignmentReportContractError) as error:
            serialize_alignment_report(report)
        _assert_error(error, "/", AlignmentReportRejectionReason.CONTENT_DRIFT)
    finally:
        object.__setattr__(report, "alignment_report_policy", original_policy)


def test_serialization_rejects_recursive_scalar_subclasses_and_bool_mutation(fx):
    class TextSubclass(str):
        pass

    class IntegerSubclass(int):
        pass

    report = _compile(fx)
    finding = report.findings[0]
    mutations = [
        (report, "project_id", TextSubclass(report.project_id)),
        (report.alignment_report_policy, "policy_version", TextSubclass(report.alignment_report_policy.policy_version)),
        (report.alignment_report_policy, "individual_warning_below_millionths", IntegerSubclass(report.alignment_report_policy.individual_warning_below_millionths)),
        (finding, "issue_code", TextSubclass(finding.issue_code)),
        (finding, "ordinal", IntegerSubclass(finding.ordinal)),
        (finding, "ordinal", True),
    ]
    for target, field, replacement in mutations:
        original = getattr(target, field)
        try:
            object.__setattr__(target, field, replacement)
            with pytest.raises(AlignmentReportContractError) as error:
                serialize_alignment_report(report)
            _assert_error(error, "/", AlignmentReportRejectionReason.CONTENT_DRIFT)
        finally:
            object.__setattr__(target, field, original)
        assert serialize_alignment_report(report)


def test_serialization_rejects_equal_value_distinct_identity_scalar_replacement(fx):
    report = _compile(fx)
    finding = report.findings[0]
    targets = [
        (report, "project_id"),
        (report.alignment_report_policy, "policy_version"),
        (finding, "issue_code"),
    ]
    for target, field in targets:
        original = getattr(target, field)
        replacement = (" " + original)[1:]
        assert replacement == original
        assert replacement is not original
        try:
            object.__setattr__(target, field, replacement)
            with pytest.raises(AlignmentReportContractError) as error:
                serialize_alignment_report(report)
            _assert_error(error, "/", AlignmentReportRejectionReason.CONTENT_DRIFT)
        finally:
            object.__setattr__(target, field, original)
        assert serialize_alignment_report(report)


def test_serialization_rejects_proxy_subclass_and_findings_container_replacement(fx):
    class ReportSubclass(AlignmentReport):
        pass

    class Proxy:
        def __init__(self, value):
            self.__dict__.update(value.__dict__)

    report = _compile(fx)
    subclass = ReportSubclass(*(getattr(report, field.name) for field in dataclasses.fields(report)))
    for value in (subclass, Proxy(report)):
        with pytest.raises(AlignmentReportContractError) as error:
            serialize_alignment_report(value)
        _assert_error(error, "/", AlignmentReportRejectionReason.NOT_MATERIALIZED)

    original = report.findings
    replacement = tuple(list(original))
    assert replacement == original and replacement is not original
    try:
        object.__setattr__(report, "findings", replacement)
        with pytest.raises(AlignmentReportContractError) as error:
            serialize_alignment_report(report)
        _assert_error(error, "/", AlignmentReportRejectionReason.CONTENT_DRIFT)
    finally:
        object.__setattr__(report, "findings", original)


def test_two_independent_equivalent_compilations_have_same_bytes_distinct_identity(fx):
    first = _compile(fx)
    second = _compile(fx)
    assert first is not second
    assert first.alignment_report_policy is not second.alignment_report_policy
    assert first.findings is not second.findings
    assert serialize_alignment_report(first) == serialize_alignment_report(second)
    assert first.alignment_report_id == second.alignment_report_id
    assert first.alignment_report_hash == second.alignment_report_hash


def test_registry_collision_rollback_and_stale_callback_are_transactional(fx, monkeypatch):
    report = _compile(fx)
    envelope = serialize_alignment_report(report)
    candidate = dataclasses.replace(report)
    other = _compile(fx)
    collision_key = id(candidate)
    collision = (weakref.ref(other), b"collision", ())
    original_collision = report_contracts._MATERIALIZED_ALIGNMENT_REPORTS.get(collision_key)
    report_contracts._MATERIALIZED_ALIGNMENT_REPORTS[collision_key] = collision
    try:
        with pytest.raises(RuntimeError, match="provenance registration failed"):
            report_contracts._register(candidate, envelope)
        assert report_contracts._MATERIALIZED_ALIGNMENT_REPORTS[collision_key] is collision
    finally:
        if original_collision is None:
            report_contracts._MATERIALIZED_ALIGNMENT_REPORTS.pop(collision_key, None)
        else:
            report_contracts._MATERIALIZED_ALIGNMENT_REPORTS[collision_key] = original_collision

    materialized = {}

    class FailingOwnerDict(dict):
        def __setitem__(self, key, value):
            raise RuntimeError("injected owner publication failure")

    monkeypatch.setattr(report_contracts, "_MATERIALIZED_ALIGNMENT_REPORTS", materialized)
    monkeypatch.setattr(report_contracts, "_OWNED_ALIGNMENT_REPORT_REFERENCES", FailingOwnerDict())
    with pytest.raises(RuntimeError, match="injected owner publication failure"):
        report_contracts._register(report, envelope)
    assert materialized == {}

    materialized = {}
    owners = {}
    monkeypatch.setattr(report_contracts, "_MATERIALIZED_ALIGNMENT_REPORTS", materialized)
    monkeypatch.setattr(report_contracts, "_OWNED_ALIGNMENT_REPORT_REFERENCES", owners)
    report_contracts._register(report, envelope)
    old_reference = materialized[id(report)][0]
    report_contracts._register(report, envelope)
    current_entry = materialized[id(report)]
    current_owner = owners[id(report)]
    assert old_reference is not current_entry[0]
    old_reference.__callback__(old_reference)
    assert materialized[id(report)] is current_entry
    assert owners[id(report)] is current_owner


def test_registry_is_weak_and_does_not_retain_report_or_dependencies(fx):
    report = _compile(fx)
    key = id(report)
    reference = weakref.ref(report)
    del report
    gc.collect()
    assert reference() is None
    assert key not in report_contracts._MATERIALIZED_ALIGNMENT_REPORTS
    assert key not in report_contracts._OWNED_ALIGNMENT_REPORT_REFERENCES


def test_report_and_registry_retain_no_dependency_or_caller_policy_objects():
    dependencies = _dependencies()
    document, revision = dependencies[1], dependencies[2]
    result = _materialize(_result_value(dependencies), dependencies)
    groups = compile_groups((document, revision, result))
    caller_policy = dataclasses.replace(POLICY)
    references = [
        weakref.ref(document), weakref.ref(revision), weakref.ref(result),
        weakref.ref(groups), weakref.ref(caller_policy),
    ]
    report = compile_alignment_report(
        narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, policy=caller_policy,
    )
    assert report.alignment_report_policy is not caller_policy
    del document, revision, result, groups, caller_policy, dependencies
    gc.collect()
    assert all(reference() is None for reference in references)
    assert serialize_alignment_report(report) == AVAILABLE_ENVELOPE_BYTES


def _genuine_null_mode(mode, monkeypatch):
    label = "UNAVAILABLE" if mode == "UNAVAILABLE" else "NOT-APPLICABLE"
    _, document, revision, audio, *_ = _dependencies()
    payload = json.loads(PAYLOAD_BYTES)
    for token in payload["tokens"]:
        token["confidence_millionths"] = None
    payload_bytes = _canonical(payload)
    raw = canonicalize_temporal_raw_package(
        {
            "schema_version": "TRP-RAW-V1",
            "run_id": "run_alignment_report_" + label,
            "raw_id": "raw_alignment_report_" + label,
            "payload": payload,
            "payload_byte_hash": "sha256:" + hashlib.sha256(payload_bytes).hexdigest(),
            "media_type": "application/vnd.kurgu.alignment-token-observation+json",
            "issue_codes": [],
        },
        payload_bytes=payload_bytes,
    )
    base = raw, document, revision, audio

    def request(request_mode):
        value = _request_value(base, request_mode)
        if mode == "NOT_APPLICABLE":
            value["adapter_capability"]["confidence_output"] = "UNSUPPORTED"
            _rehash(value, "alignment_request_id", "alignment_request_hash", "arq_")
        return materialize_alignment_request(
            value, temporal_raw_package=raw, narration_document=document,
            narration_revision=revision, audio_artifact=audio,
        )

    source_request = request("LOCAL")
    source_value = _execution_value(source_request, "LOCAL")
    source_value["confidence_availability_evidence"]["availability"] = mode
    _rehash(source_value, "adapter_execution_id", "adapter_execution_hash", "aex_")
    source_execution = materialize_adapter_execution(
        source_value, alignment_request=source_request,
    )
    request_value = request("REPLAY")
    replay = {
        "schema_version": "REPLAY-EVIDENCE-V1",
        "source_adapter_execution_id": source_execution.adapter_execution_id,
        "source_adapter_execution_hash": source_execution.adapter_execution_hash,
        "source_alignment_request_id": source_request.alignment_request_id,
        "source_alignment_request_hash": source_request.alignment_request_hash,
    }
    execution_value = _execution_value(request_value, "REPLAY", replay=replay)
    execution_value["confidence_availability_evidence"]["availability"] = mode
    _rehash(execution_value, "adapter_execution_id", "adapter_execution_hash", "aex_")
    execution = materialize_adapter_execution(
        execution_value, alignment_request=request_value,
        source_alignment_request=source_request, source_execution=source_execution,
    )
    document_bytes = _canonical(narration_contracts._document_to_dict(document))
    evidence = {
        "schema_version": result_contracts.TIMING_ORIGIN_EVIDENCE_V1,
        "hash_scope_version": result_contracts.TIMING_ORIGIN_EVIDENCE_HASH_V1,
        "timing_origin_evidence_id": "toe_" + "0" * 32,
        "timing_origin_evidence_hash": "0" * 64,
        "fixture_id": "FX-ALREP-" + label + "-TIMING",
        "temporal_raw_package_hash": raw.canonical_hash,
        "timing_payload_byte_hash": "sha256:" + hashlib.sha256(payload_bytes).hexdigest(),
        "narration_document_snapshot_hash": "sha256:" + hashlib.sha256(document_bytes).hexdigest(),
        "narration_revision_id": revision.revision_id,
        "narration_revision_hash": revision.revision_hash,
        "audio_artifact_id": audio.audio_artifact_id,
        "audio_artifact_hash": audio.audio_artifact_hash,
        "alignment_request_id": request_value.alignment_request_id,
        "alignment_request_hash": request_value.alignment_request_hash,
        "adapter_execution_id": execution.adapter_execution_id,
        "adapter_execution_hash": execution.adapter_execution_hash,
    }
    _rehash(evidence, "timing_origin_evidence_id", "timing_origin_evidence_hash", "toe_")
    evidence_bytes = _canonical(evidence)
    key = (
        evidence["fixture_id"], evidence["timing_origin_evidence_hash"],
        hashlib.sha256(evidence_bytes).hexdigest(), len(evidence_bytes),
        hashlib.sha256(payload_bytes).hexdigest(), len(payload_bytes),
    )
    monkeypatch.setattr(
        result_contracts, "_allowlist_lookup",
        lambda candidate: (evidence_bytes, payload_bytes) if candidate == key else None,
    )
    monkeypatch.setattr(result_contracts, "_GOLDEN_EVIDENCE", evidence_bytes)
    monkeypatch.setattr(result_contracts, "_GOLDEN_TIMING_PAYLOAD", payload_bytes)
    timing_evidence = load_repository_timing_origin_evidence(evidence_bytes)
    value = _result_value((raw, document, revision, audio, request_value, execution, timing_evidence))
    value["confidence_availability"] = mode
    for timing in value["word_timings"]:
        timing["confidence_millionths"] = None
    _rehash(value, "alignment_result_id", "alignment_result_hash", "alr_")
    result = materialize_alignment_result(
        value, temporal_raw_package=raw, narration_document=document,
        narration_revision=revision, audio_artifact=audio,
        alignment_request=request_value, adapter_execution=execution,
        timing_origin_evidence=timing_evidence,
    )
    groups = compile_caption_groups(
        narration_document=document, narration_revision=revision,
        alignment_result=result,
    )
    return document, revision, result, groups


@pytest.mark.parametrize(
    "mode,expected_id,expected_sha,expected_envelope,expected_status,expected_warnings",
    [
        (
            "UNAVAILABLE", "alrep_1b52419d9c9e41dbfc7a6f4517d5909e",
            "64b9facf58d6790596c85c299714ac4f8b7b52c308d1ad532548ec8c369d1c33",
            UNAVAILABLE_ENVELOPE_BYTES,
            AlignmentReportStatus.CONFIDENCE_UNAVAILABLE, 1,
        ),
        (
            "NOT_APPLICABLE", "alrep_0d777cf83342fc7e399fe98eaa500732",
            "b894b07465ba77d1111db6fe84b3e254766480deefb85b7a242a1f05462e27de",
            NOT_APPLICABLE_ENVELOPE_BYTES,
            AlignmentReportStatus.CONFIDENCE_NOT_APPLICABLE, 0,
        ),
    ],
)
def test_genuine_null_confidence_modes_and_frozen_goldens(
    mode, expected_id, expected_sha, expected_envelope, expected_status,
    expected_warnings, monkeypatch,
):
    document, revision, result, groups = _genuine_null_mode(mode, monkeypatch)
    report = compile_alignment_report(
        narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, policy=POLICY,
    )
    envelope = serialize_alignment_report(report)
    assert report.alignment_report_id == expected_id
    assert hashlib.sha256(envelope).hexdigest() == expected_sha
    assert envelope == expected_envelope
    assert report.status is expected_status
    assert report.evaluated_word_confidence_count == 0
    assert report.evaluated_caption_group_confidence_count == 0
    assert report.minimum_word_confidence_millionths is None
    assert report.minimum_caption_group_confidence_millionths is None
    assert report.low_confidence_word_ratio_millionths is None
    assert report.warning_finding_count == expected_warnings
    if mode == "UNAVAILABLE":
        assert [item.issue_code for item in report.findings] == ["CONFIDENCE_UNAVAILABLE"]
        assert report.findings[0].observed_millionths is None
        assert report.findings[0].threshold_millionths is None
    else:
        assert report.findings == ()


def test_error_messages_never_echo_attacker_values(fx):
    envelope = serialize_alignment_report(_compile(fx))
    document, revision, result, groups = fx
    attacker = "attacker-secret-path-value"
    value = json.loads(envelope)
    value[attacker] = attacker
    source = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(AlignmentReportContractError) as error:
        load_alignment_report(
            source, narration_document=document, narration_revision=revision,
            alignment_result=result, caption_groups=groups, policy=POLICY,
        )
    assert attacker not in str(error.value)


def test_no_frame_or_io_coupling_static():
    source = inspect.getsource(report_contracts)
    for forbidden in (
        "word_to_frame", "WordToFrameArtifact", "open(", "requests", "subprocess",
        "threading", "time.time", "random.", "v2.",
    ):
        assert forbidden not in source
