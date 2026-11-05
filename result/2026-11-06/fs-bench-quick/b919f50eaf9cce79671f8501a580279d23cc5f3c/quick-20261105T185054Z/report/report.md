# fs-bench-quick campaign report

> Status: Research; informative and not a product contract.

**Diagnostic execution/cleanup outcome: PASS.** Final infrastructure cleanup: COMPLETE.

Registered rows: 96. Execution outcomes: {'PASS': 96}. Performance-eligible rows: 0. Independently verified rows: 0.

Raw CLI observations include launch, routing and Store open/close costs. Unverified rows are diagnostics. Ineligible observations establish no speed comparison. Cleanup completion is reported separately in the campaign cleanup receipt.

End-to-end case time includes Sandbox creation, mount, Exec, LayerFS Commit, unmount and case cleanup. It excludes preparation and initial Python startup/configuration checks.

| Case / machine / database | Execution | Performance | Verification | Cleanup | Exec ns | End-to-end case ns | Reason |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| [C01/native/sqlite](../receipts/C01/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 767369125 | 1967745250 |  |
| [C01/native/postgresql](../receipts/C01/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 548099500 | 1049662084 |  |
| [C01/docker/sqlite](../receipts/C01/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 304020041 | 995929916 |  |
| [C01/docker/postgresql](../receipts/C01/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 169980125 | 1272372125 |  |
| [C01/lima/sqlite](../receipts/C01/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 207930166 | 3614305291 |  |
| [C01/lima/postgresql](../receipts/C01/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 214629542 | 1626245583 |  |
| [C01/apple-container/sqlite](../receipts/C01/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 209383250 | 2282536708 |  |
| [C01/apple-container/postgresql](../receipts/C01/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 260677750 | 1162370917 |  |
| [C02/native/sqlite](../receipts/C02/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 4175699708 | 4528140417 |  |
| [C02/native/postgresql](../receipts/C02/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 4435326250 | 4980095959 |  |
| [C02/docker/sqlite](../receipts/C02/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 732275583 | 1503926917 |  |
| [C02/docker/postgresql](../receipts/C02/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 640644750 | 1797625333 |  |
| [C02/lima/sqlite](../receipts/C02/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 571180541 | 1637870833 |  |
| [C02/lima/postgresql](../receipts/C02/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 567188333 | 1997519666 |  |
| [C02/apple-container/sqlite](../receipts/C02/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 564629292 | 891395458 |  |
| [C02/apple-container/postgresql](../receipts/C02/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 554471584 | 1431471834 |  |
| [C03/native/sqlite](../receipts/C03/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 924207000 | 1230555917 |  |
| [C03/native/postgresql](../receipts/C03/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 962564458 | 1447034917 |  |
| [C03/docker/sqlite](../receipts/C03/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 460792042 | 1182779833 |  |
| [C03/docker/postgresql](../receipts/C03/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 410962291 | 1459311125 |  |
| [C03/lima/sqlite](../receipts/C03/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 355016333 | 1373347167 |  |
| [C03/lima/postgresql](../receipts/C03/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 352483834 | 1705740625 |  |
| [C03/apple-container/sqlite](../receipts/C03/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 409485334 | 695977917 |  |
| [C03/apple-container/postgresql](../receipts/C03/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 383695834 | 1103895417 |  |
| [C04/native/sqlite](../receipts/C04/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 3661644958 | 4130008916 |  |
| [C04/native/postgresql](../receipts/C04/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 3266967208 | 4001331834 |  |
| [C04/docker/sqlite](../receipts/C04/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 684792125 | 1533489375 |  |
| [C04/docker/postgresql](../receipts/C04/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 641166750 | 1987293958 |  |
| [C04/lima/sqlite](../receipts/C04/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 598293083 | 1769663375 |  |
| [C04/lima/postgresql](../receipts/C04/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 650992625 | 2304403083 |  |
| [C04/apple-container/sqlite](../receipts/C04/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 593074208 | 1029263792 |  |
| [C04/apple-container/postgresql](../receipts/C04/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 550042000 | 1581554417 |  |
| [C05/native/sqlite](../receipts/C05/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 2983955958 | 3481210166 |  |
| [C05/native/postgresql](../receipts/C05/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 3395906958 | 4193451167 |  |
| [C05/docker/sqlite](../receipts/C05/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 727545041 | 1624484459 |  |
| [C05/docker/postgresql](../receipts/C05/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 700074333 | 2091755834 |  |
| [C05/lima/sqlite](../receipts/C05/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 525940208 | 1710462875 |  |
| [C05/lima/postgresql](../receipts/C05/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 523989708 | 2134490167 |  |
| [C05/apple-container/sqlite](../receipts/C05/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 509204041 | 967559167 |  |
| [C05/apple-container/postgresql](../receipts/C05/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 495320875 | 1552187459 |  |
| [C06/native/sqlite](../receipts/C06/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 136762500 | 819870000 |  |
| [C06/native/postgresql](../receipts/C06/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 168295166 | 1094478375 |  |
| [C06/docker/sqlite](../receipts/C06/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 225987708 | 1383925750 |  |
| [C06/docker/postgresql](../receipts/C06/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 147216041 | 1552292875 |  |
| [C06/lima/sqlite](../receipts/C06/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 105636583 | 1471474959 |  |
| [C06/lima/postgresql](../receipts/C06/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 110481917 | 1834225792 |  |
| [C06/apple-container/sqlite](../receipts/C06/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 162938791 | 831796458 |  |
| [C06/apple-container/postgresql](../receipts/C06/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 168833292 | 1305506250 |  |
| [C07/native/sqlite](../receipts/C07/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 272813500 | 1211501458 |  |
| [C07/native/postgresql](../receipts/C07/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 292024666 | 1492368916 |  |
| [C07/docker/sqlite](../receipts/C07/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 315666667 | 1675559291 |  |
| [C07/docker/postgresql](../receipts/C07/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 287807292 | 2095110916 |  |
| [C07/lima/sqlite](../receipts/C07/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 294932333 | 1945355042 |  |
| [C07/lima/postgresql](../receipts/C07/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 229766666 | 2224705458 |  |
| [C07/apple-container/sqlite](../receipts/C07/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 265431833 | 1227101208 |  |
| [C07/apple-container/postgresql](../receipts/C07/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 284296208 | 1678679833 |  |
| [C08/native/sqlite](../receipts/C08/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 149358250 | 879522333 |  |
| [C08/native/postgresql](../receipts/C08/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 165613084 | 1087990584 |  |
| [C08/docker/sqlite](../receipts/C08/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 142227583 | 1275588500 |  |
| [C08/docker/postgresql](../receipts/C08/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 158559292 | 1710299333 |  |
| [C08/lima/sqlite](../receipts/C08/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 127248125 | 1582721625 |  |
| [C08/lima/postgresql](../receipts/C08/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 122223458 | 1934332083 |  |
| [C08/apple-container/sqlite](../receipts/C08/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 157583417 | 891530667 |  |
| [C08/apple-container/postgresql](../receipts/C08/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 168787959 | 1432961166 |  |
| [C09/native/sqlite](../receipts/C09/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 44333167 | 570357459 |  |
| [C09/native/postgresql](../receipts/C09/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 68446958 | 776381958 |  |
| [C09/docker/sqlite](../receipts/C09/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 78692750 | 972007375 |  |
| [C09/docker/postgresql](../receipts/C09/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 113670542 | 1333644958 |  |
| [C09/lima/sqlite](../receipts/C09/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 48063000 | 1295717250 |  |
| [C09/lima/postgresql](../receipts/C09/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 56066167 | 1557055333 |  |
| [C09/apple-container/sqlite](../receipts/C09/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 78408083 | 576766583 |  |
| [C09/apple-container/postgresql](../receipts/C09/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 113744625 | 1055968000 |  |
| [C10/native/sqlite](../receipts/C10/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 163876000 | 799137584 |  |
| [C10/native/postgresql](../receipts/C10/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 190778708 | 1031299417 |  |
| [C10/docker/sqlite](../receipts/C10/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 184331125 | 1251752417 |  |
| [C10/docker/postgresql](../receipts/C10/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 204382750 | 1531324542 |  |
| [C10/lima/sqlite](../receipts/C10/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 170859667 | 1570790500 |  |
| [C10/lima/postgresql](../receipts/C10/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 178602291 | 1836646334 |  |
| [C10/apple-container/sqlite](../receipts/C10/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 190664416 | 836146083 |  |
| [C10/apple-container/postgresql](../receipts/C10/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 243947208 | 1412768625 |  |
| [C11/native/sqlite](../receipts/C11/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 117556583 | 922398375 |  |
| [C11/native/postgresql](../receipts/C11/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 141612875 | 1170984833 |  |
| [C11/docker/sqlite](../receipts/C11/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 120701208 | 1291273583 |  |
| [C11/docker/postgresql](../receipts/C11/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 113935959 | 1513443292 |  |
| [C11/lima/sqlite](../receipts/C11/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 92822208 | 1630891458 |  |
| [C11/lima/postgresql](../receipts/C11/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 91170958 | 1884140250 |  |
| [C11/apple-container/sqlite](../receipts/C11/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 114013291 | 887329666 |  |
| [C11/apple-container/postgresql](../receipts/C11/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 171133417 | 1372883125 |  |
| [C12/native/sqlite](../receipts/C12/native/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 325582584 | 1037385250 |  |
| [C12/native/postgresql](../receipts/C12/native/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 347293333 | 1317640792 |  |
| [C12/docker/sqlite](../receipts/C12/docker/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 191522708 | 1324510458 |  |
| [C12/docker/postgresql](../receipts/C12/docker/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 215242375 | 1796868542 |  |
| [C12/lima/sqlite](../receipts/C12/lima/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 101122042 | 1543651750 |  |
| [C12/lima/postgresql](../receipts/C12/lima/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 138426875 | 2001963458 |  |
| [C12/apple-container/sqlite](../receipts/C12/apple-container/sqlite/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 166190792 | 864936625 |  |
| [C12/apple-container/postgresql](../receipts/C12/apple-container/postgresql/receipt.json) | PASS | INELIGIBLE | SKIPPED | COMPLETE | 191504208 | 1530757375 |  |

## Database comparisons

Ratio = PostgreSQL CLI exec ns / SQLite CLI exec ns. Delta = PostgreSQL ns - SQLite ns. Only eligible matched rows receive a ratio.

| Cell / machine | Delta ns | Ratio | Disposition |
| --- | ---: | ---: | --- |
| C01/native |  |  | INELIGIBLE or incomplete pair |
| C01/docker |  |  | INELIGIBLE or incomplete pair |
| C01/lima |  |  | INELIGIBLE or incomplete pair |
| C01/apple-container |  |  | INELIGIBLE or incomplete pair |
| C02/native |  |  | INELIGIBLE or incomplete pair |
| C02/docker |  |  | INELIGIBLE or incomplete pair |
| C02/lima |  |  | INELIGIBLE or incomplete pair |
| C02/apple-container |  |  | INELIGIBLE or incomplete pair |
| C03/native |  |  | INELIGIBLE or incomplete pair |
| C03/docker |  |  | INELIGIBLE or incomplete pair |
| C03/lima |  |  | INELIGIBLE or incomplete pair |
| C03/apple-container |  |  | INELIGIBLE or incomplete pair |
| C04/native |  |  | INELIGIBLE or incomplete pair |
| C04/docker |  |  | INELIGIBLE or incomplete pair |
| C04/lima |  |  | INELIGIBLE or incomplete pair |
| C04/apple-container |  |  | INELIGIBLE or incomplete pair |
| C05/native |  |  | INELIGIBLE or incomplete pair |
| C05/docker |  |  | INELIGIBLE or incomplete pair |
| C05/lima |  |  | INELIGIBLE or incomplete pair |
| C05/apple-container |  |  | INELIGIBLE or incomplete pair |
| C06/native |  |  | INELIGIBLE or incomplete pair |
| C06/docker |  |  | INELIGIBLE or incomplete pair |
| C06/lima |  |  | INELIGIBLE or incomplete pair |
| C06/apple-container |  |  | INELIGIBLE or incomplete pair |
| C07/native |  |  | INELIGIBLE or incomplete pair |
| C07/docker |  |  | INELIGIBLE or incomplete pair |
| C07/lima |  |  | INELIGIBLE or incomplete pair |
| C07/apple-container |  |  | INELIGIBLE or incomplete pair |
| C08/native |  |  | INELIGIBLE or incomplete pair |
| C08/docker |  |  | INELIGIBLE or incomplete pair |
| C08/lima |  |  | INELIGIBLE or incomplete pair |
| C08/apple-container |  |  | INELIGIBLE or incomplete pair |
| C09/native |  |  | INELIGIBLE or incomplete pair |
| C09/docker |  |  | INELIGIBLE or incomplete pair |
| C09/lima |  |  | INELIGIBLE or incomplete pair |
| C09/apple-container |  |  | INELIGIBLE or incomplete pair |
| C10/native |  |  | INELIGIBLE or incomplete pair |
| C10/docker |  |  | INELIGIBLE or incomplete pair |
| C10/lima |  |  | INELIGIBLE or incomplete pair |
| C10/apple-container |  |  | INELIGIBLE or incomplete pair |
| C11/native |  |  | INELIGIBLE or incomplete pair |
| C11/docker |  |  | INELIGIBLE or incomplete pair |
| C11/lima |  |  | INELIGIBLE or incomplete pair |
| C11/apple-container |  |  | INELIGIBLE or incomplete pair |
| C12/native |  |  | INELIGIBLE or incomplete pair |
| C12/docker |  |  | INELIGIBLE or incomplete pair |
| C12/lima |  |  | INELIGIBLE or incomplete pair |
| C12/apple-container |  |  | INELIGIBLE or incomplete pair |

## Machine comparisons

Ratio = guest CLI exec ns / native CLI exec ns, within the same cell and database. Only eligible matched rows receive a ratio.

| Cell / database / guest | Delta ns vs native | Ratio | Disposition |
| --- | ---: | ---: | --- |
| C01/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C01/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C01/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C01/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C01/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C01/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C02/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C02/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C02/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C02/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C02/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C02/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C03/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C03/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C03/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C03/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C03/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C03/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C04/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C04/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C04/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C04/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C04/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C04/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C05/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C05/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C05/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C05/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C05/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C05/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C06/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C06/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C06/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C06/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C06/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C06/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C07/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C07/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C07/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C07/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C07/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C07/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C08/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C08/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C08/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C08/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C08/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C08/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C09/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C09/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C09/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C09/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C09/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C09/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C10/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C10/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C10/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C10/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C10/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C10/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C11/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C11/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C11/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C11/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C11/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C11/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
| C12/sqlite/docker |  |  | INELIGIBLE or incomplete pair |
| C12/sqlite/lima |  |  | INELIGIBLE or incomplete pair |
| C12/sqlite/apple-container |  |  | INELIGIBLE or incomplete pair |
| C12/postgresql/docker |  |  | INELIGIBLE or incomplete pair |
| C12/postgresql/lima |  |  | INELIGIBLE or incomplete pair |
| C12/postgresql/apple-container |  |  | INELIGIBLE or incomplete pair |
