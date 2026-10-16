# Análisis de PENSUMO y guía para construir algo similar

> Documento de trabajo. Las cifras públicas sobre Pensumo varían según la fuente y la fecha; se indican como orientativas. Los aspectos legales y fiscales deben validarse con un asesor especializado antes de lanzar nada.

---

## 1. Qué es Pensumo

**Pensumo** (de *pensión* + *consumo*) es una app española que convierte el gasto cotidiano en **ahorro para la jubilación**. Cuando un usuario compra en un comercio adherido, el comercio aporta un porcentaje de la venta a un **plan de pensiones individual** del usuario. Es un *cashback*, pero en lugar de devolver el dinero a un monedero disponible, lo bloquea como ahorro a largo plazo.

| Dato | Detalle |
|---|---|
| Origen | Idea de José Luis Orós («Sistema Pensión por Consumo»). Proyecto con Ibercaja desde ~2018. |
| Regulación | Probado durante ~2 años en el **sandbox financiero** español (Tesoro + DGSFP). Elegido entre 18 de 67 proyectos de la cohorte. |
| Sociedad | Ibercaja constituye Pensumo como empresa tras el sandbox. |
| Lanzamiento | Octubre 2024; abierto a clientes de **cualquier banco** español a finales de octubre 2024. |
| Producto financiero | Plan de pensiones gestionado por **Ibercaja Pensión** (fondo mixto de renta fija internacional, según prensa). |
| Socio tecnológico | **Coinscrap Finance** (agregación de datos transaccionales y marketplace de compras online: Decathlon, Ikea, Lidl, Fnac, MediaMarkt, Lego, Adidas, Sephora…). |
| Comercios | ~100–140 adheridos en el lanzamiento (las fuentes no coinciden). |
| Precio usuario | Gratuita. |

---

## 2. Cómo funciona (vista de producto)

### 2.1 Fuentes de aportación

1. **Compras en comercios adheridos (físicos)** – el usuario paga con su tarjeta vinculada; la app detecta la operación y el comercio aporta un % (prensa: entre 1 % y 6 %, algunos acuerdos hasta 20 %).
2. **Compras online** – a través del marketplace dentro de la app (enlaces de afiliación); la comisión de afiliado se convierte en aportación.
3. **Retos / hábitos saludables** – incentivos por actividades medibles (reciclar, correr, leer…), financiados por patrocinadores o campañas.
4. **Ahorro voluntario del usuario** (anunciado como evolución): % fijo, cantidad mensual o **redondeo** de cada compra.

### 2.2 Recorrido del usuario

```
Descarga app → Registro + KYC → Contrata/abre plan de pensiones
     → Vincula tarjetas/cuentas (PSD2) → Compra en comercio adherido
     → Transacción detectada → Aportación "pendiente"
     → Pasa periodo de devolución → Aportación "confirmada"
     → Liquidación periódica al plan → Participaciones en el fondo
```

Clave: **el usuario no escanea tickets ni hace nada extra**; todo es automático tras vincular la tarjeta.

### 2.3 Propuesta de valor por actor

| Actor | Qué gana |
|---|---|
| Usuario | Ahorro para la jubilación «sin esfuerzo»; app gratuita; sin cambiar de banco. |
| Comercio | Captación y fidelización; solo paga por venta realizada (modelo performance); imagen de responsabilidad social. |
| Gestora/banco (Ibercaja) | Captación de partícipes jóvenes y de otros bancos; activos bajo gestión; datos. |
| Pensumo | Margen sobre la comisión del comercio + comisiones de afiliación. |

---

## 3. Modelo de negocio

Ejemplo citado en prensa: compra de **100 €** → el comercio paga **3 €** → **2 €** al plan del usuario y **1 €** de margen para la plataforma.

Fuentes de ingresos:

- **Fee sobre ventas** de comercios adheridos (split comercio → usuario / plataforma).
- **Comisiones de afiliación** online (Awin, Tradedoubler, programas directos…): la plataforma cobra el CPA y entrega parte al usuario.
- **Campañas patrocinadas** (retos, marcas).
- Indirectos para el grupo financiero: **comisión de gestión y depósito** del fondo de pensiones sobre el patrimonio acumulado.

Retos del modelo:

- Las aportaciones por usuario son pequeñas (decenas de €/año) → la plataforma solo es rentable con **mucha escala** o si el socio financiero monetiza el patrimonio.
- Problema del huevo y la gallina (usuarios ↔ comercios).
- Los cashback «a cuenta» son más atractivos a corto plazo que un ahorro bloqueado décadas.

---

## 4. Marco regulatorio (España) – lo que hay que resolver

| Área | Implicación | Cómo lo resolvió Pensumo / alternativas |
|---|---|---|
| **Planes de pensiones** (RDL 1/2002 TRLPFP, RD 304/2004) | Solo una **entidad gestora** autorizada por la DGSFP con **entidad depositaria** puede gestionarlos. Ilíquidos salvo supuestos de rescate (incl. aportaciones con 10 años de antigüedad). Límite de aportación anual. | Ibercaja Pensión como gestora. Tú necesitarías **acuerdo con una gestora** (white-label) o usar otro vehículo. |
| **Aportaciones de terceros** | Que un comercio aporte al plan de un particular no encaja de forma estándar en la normativa → por eso pasó por el **sandbox**. | Alternativas: el comercio paga a la plataforma, la plataforma abona al usuario y este (o un mandato) aporta; o usar **PIAS / seguro de ahorro / fondo de inversión** en vez de plan de pensiones. |
| **PSD2 / Open Banking** (RDL 19/2018) | Leer movimientos de cuentas requiere licencia **AISP** del Banco de España o ser agente de un proveedor licenciado. | Coinscrap / proveedores tipo Tink, Salt Edge, Unnax, Afterbanks… |
| **Card-linked offers** | Alternativa a PSD2: programas de Visa/Mastercard que notifican compras con tarjetas inscritas. | Proveedores tipo Fidel API. |
| **Distribución de seguros** (si usas PIAS/seguro) | Ley de Distribución de Seguros (RDL 3/2020): agente/operador vinculado de una aseguradora. | Acuerdo con aseguradora. |
| **Prevención de blanqueo (Ley 10/2010)** | KYC del partícipe. | Normalmente lo asume la gestora/aseguradora; la app captura datos y documentos. |
| **Protección de datos (RGPD + LOPDGDD)** | Datos transaccionales = alto riesgo de perfilado. EIPD obligatoria, consentimientos granulares. | DPO, minimización, cifrado. |
| **Fiscalidad** | Tratamiento IRPF de las aportaciones por terceros y del cashback: **validar con la DGT/asesor**. | Clave en el diseño del producto. |
| **Publicidad financiera** | Orden EHA/1718/2010 y circulares del Banco de España / DGSFP. | Revisión legal de mensajes. |

**Conclusión regulatoria:** la vía realista para un nuevo actor es **no tener licencias propias** al principio y actuar como **capa tecnológica + agente** de una gestora/aseguradora y de un proveedor PSD2. Valorar presentar el proyecto al **sandbox** si el modelo requiere cambios normativos.

---

## 5. Arquitectura técnica propuesta para un producto similar

### 5.1 Componentes

```
┌─────────────────────┐    ┌──────────────────────┐
│ App móvil (Flutter/ │    │ Portal comercios     │
│ React Native)       │    │ (web, React)         │
└─────────┬───────────┘    └──────────┬───────────┘
          │  HTTPS / JWT              │
┌─────────▼───────────────────────────▼───────────┐
│                  API Gateway                    │
└──┬────────┬─────────┬─────────┬────────┬────────┘
   │        │         │         │        │
 Users   Linking   Rewards   Merchants  Payouts
 & KYC   (PSD2 /   Engine    & Offers   (gestora)
         CLO)      (reglas)
   │        │         │         │        │
   └────────┴────┬────┴─────────┴────────┘
                 │  eventos (Kafka / SQS / Pub/Sub)
         ┌───────▼────────┐   ┌───────────────┐
         │ PostgreSQL     │   │ Ledger contable│
         │ (datos núcleo) │   │ doble entrada  │
         └────────────────┘   └───────────────┘

Integraciones externas:
 - Agregador PSD2 (Tink / Salt Edge / Coinscrap…)
 - Card-linked offers (Fidel API, programas Visa/MC)
 - Redes de afiliación (Awin, Tradedoubler, Admitad…)
 - Gestora de pensiones / aseguradora (API o fichero SFTP)
 - KYC (Onfido, Veriff, IDnow…) si no lo hace la gestora
 - Pasarela de cobro a comercios (SEPA Direct Debit: GoCardless, Stripe)
```

### 5.2 Flujo de una transacción

1. **Ingesta**: webhook del agregador PSD2 / CLO con la operación (importe, fecha, descripción, MCC, terminal).
2. **Normalización y matching**: identificar el comercio (texto del descriptor, MCC, ID de terminal, geolocalización). Es la parte más difícil: el descriptor bancario es ruidoso → reglas + diccionario + modelo ML de clasificación.
3. **Motor de reglas**: aplicar la oferta vigente (% , tope, días/horas, primera compra, categorías).
4. **Estado `PENDING`** en el ledger: el usuario ve la aportación pendiente.
5. **Periodo de validación** (14–30 días para devoluciones; en afiliación online, hasta 60–90 días).
6. **Cobro al comercio** (SEPA mensual) → `CONFIRMED`.
7. **Liquidación agregada** a la gestora (mensual) con el detalle por partícipe → `INVESTED`.
8. **Conciliación** con el extracto de la gestora (participaciones, valor liquidativo).

### 5.3 Modelo de datos mínimo

```sql
users(id, email, phone, kyc_status, created_at)
pension_accounts(id, user_id, provider, external_account_id, status)
linked_cards(id, user_id, provider, token, last4, status, consent_expires_at)
merchants(id, name, cif, iban_mandate_id, status)
merchant_locations(id, merchant_id, descriptor_pattern, mcc, terminal_id, lat, lng)
offers(id, merchant_id, pct, max_per_tx, valid_from, valid_to, rules_json)
transactions(id, user_id, card_id, amount, currency, booked_at, raw_descriptor,
             mcc, matched_merchant_id, match_confidence, status)
rewards(id, transaction_id, user_id, offer_id, user_amount, platform_amount,
        status /* PENDING|CONFIRMED|REVERSED|INVESTED */, confirmed_at)
ledger_entries(id, journal_id, account, debit, credit, created_at)  -- inmutable
payout_batches(id, provider, period, total_amount, status, file_ref)
challenges(id, sponsor_id, type, target, reward_amount, valid_to)
challenge_progress(id, user_id, challenge_id, progress, completed_at)
```

Principios: importes en **céntimos (enteros)**, ledger **inmutable de doble entrada**, idempotencia en webhooks, auditoría completa.

### 5.4 Stack recomendado (MVP)

- **Móvil**: Flutter o React Native (una base de código iOS/Android).
- **Backend**: Python (FastAPI) o Node (NestJS); PostgreSQL; colas (SQS/Pub/Sub); Redis.
- **Cloud**: AWS o GCP en región UE (Frankfurt/Madrid) por RGPD.
- **Auth**: Auth0/Cognito/Keycloak + biometría en el dispositivo.
- **Observabilidad**: Sentry, Grafana/Datadog; registros de auditoría separados.
- **Seguridad**: cifrado en reposo, secretos en KMS, pentest antes de salir, no almacenar PAN de tarjetas (solo tokens del proveedor).

---

## 6. Funcionalidades de la app

**MVP**
- Registro, KYC, alta en el producto de ahorro del socio.
- Vinculación de tarjetas/cuentas (PSD2).
- Mapa y listado de comercios con % de aportación.
- Marketplace online (enlaces de afiliación).
- Panel: total ahorrado, pendiente vs. confirmado, histórico por comercio.
- Notificaciones push («Has generado 1,20 € para tu jubilación en X»).

**Fase 2**
- Redondeos y aportaciones periódicas voluntarias.
- Retos patrocinados (pasos vía HealthKit/Google Fit, reciclaje con QR…).
- **Simulador de jubilación** (proyección con rentabilidad y aportaciones).
- Programa de referidos.

**Portal de comercios**
- Alta, mandato SEPA, configuración de ofertas, panel de ventas atribuidas, facturas.

---

## 7. Hoja de ruta sugerida

| Fase | Duración orientativa | Objetivo |
|---|---|---|
| 0. Validación | 1–2 meses | Entrevistas a 30–50 comercios y usuarios; elegir vehículo (plan de pensiones vs. PIAS vs. fondo); conversaciones con 2–3 gestoras/aseguradoras y proveedores PSD2; consulta legal/fiscal. |
| 1. Piloto «concierge» | 2–3 meses | Una ciudad/barrio, 20–30 comercios, 500 usuarios. Matching semiautomático, liquidaciones manuales. Medir uso, aportación media y retención. |
| 2. MVP | 4–6 meses | App + backend + portal comercios; integraciones PSD2, afiliación, gestora; ledger. |
| 3. Escala | continuo | Grandes cadenas, CLO con Visa/MC, retos patrocinados, B2B (empresas que aportan por empleados). |

Valorar el **sandbox financiero** (Ley 7/2020) si el modelo requiere aportaciones de terceros directas a planes de pensiones.

---

## 8. Riesgos y cómo mitigarlos

| Riesgo | Mitigación |
|---|---|
| Dependencia de la gestora/socio bancario | Diseñar la capa de pagos multi-proveedor; contrato con SLA y portabilidad. |
| Baja aportación percibida por el usuario | Gamificación, simulador de jubilación, retos y campañas con % elevados en el arranque. |
| Matching de transacciones erróneo | Revisión manual en piloto, ML + reclamaciones del usuario dentro de la app. |
| Comercios que no pagan | Mandato SEPA previo; no confirmar aportación hasta cobrar. |
| Costes de PSD2 por usuario | Negociar por volumen; CLO como alternativa; limitar refrescos de datos. |
| Cambios regulatorios / fiscales | Asesoría continua; sandbox. |
| Competencia (cashback clásico, apps de redondeo, bancos) | Diferenciación social (jubilación), alianzas con asociaciones de comercio local y ayuntamientos. |

---

## 9. Ideas de diferenciación frente a Pensumo

- **Comercio de proximidad**: alianzas con asociaciones de comerciantes y ayuntamientos (bonos de consumo que se convierten en ahorro).
- **Vehículo flexible**: además de plan de pensiones, opción de fondo indexado / PIAS para quienes valoran liquidez.
- **Modelo B2B2C**: empresas que aportan por cada compra de sus empleados como beneficio social.
- **Transparencia total**: mostrar el split comercio/usuario/plataforma en cada aportación.
- **Mercados fuera de España** (Latinoamérica) con sistemas de pensiones complementarios.

---

## Fuentes

- [Vozpópuli – ¿Es posible completar la pensión comprando en Amazon?](https://www.vozpopuli.com/economia/startups/es-posible-completar-pension-comprando-amazon-pensiones-ahorrar_0_1117088749.html)
- [Merca2 – La «pensión por consumo», alternativa a los planes de pensiones privados (2018)](https://www.merca2.es/2018/12/26/la-pension-por-consumo-alternativa-a-los-planes-de-pensiones-privados-97618/)
- [Merca2 – Ibercaja experimenta los usos de Pensumo en el sandbox financiero (2021)](https://www.merca2.es/2021/12/28/ibercaja-plataforma-pensumo-sandbox-838418/)
- [Moncloa.com – El beneficio social de la «pensión por consumo» (2023)](https://www.moncloa.com/2023/02/08/el-beneficio-social-de-la-pension-por-consumo-1842152/)
- [Funds Society – Ibercaja constituye una nueva empresa de ahorro basado en el consumo](https://www.fundssociety.com/es/noticias/negocio/ibercaja-constituye-una-nueva-empresa-de-ahorro-basado-en-el-consumo/)
- [Funds Society – Ibercaja lanza la app Pensumo](https://www.fundssociety.com/es/formate-a-fondo/ibercaja-lanza-la-app-pensumo-destinada-al-ahorro-para-la-jubilacion/)
- [El Español – Ibercaja lanza una app para ahorrar en pensiones cuando compras en Amazon, Ikea, Lidl o Decathlon (2024)](https://www.elespanol.com/invertia/mis-finanzas/planes-pensiones/20241002/ibercaja-lanza-app-ahorrar-pensiones-compras-amazon-ikea-lidl-decathlon/890411297_0.html)
- [Hoy Aragón – Ibercaja abre Pensumo a toda la banca española (2024)](https://www.hoyaragon.es/articulo/noticias-economia-empresa/ibercaja-pensumo-ahorro-jubilacion/20241025114644078212.html)
- [SegurosNews – Ibercaja lanza Pensumo](https://segurosnews.com/news/ibercaja-lanza-pensumo-para-impulsar-el-ahorro-para-la-jubilacion-ligada-a-los-habitos-de-consumo)
- [Coinscrap Finance – Ibercaja y Coinscrap lanzan Pensumo](https://coinscrapfinance.com/fintech-news/ibercaja-coinscrap-finance-launch-pensumo/)
- [Dealroom – Pensumo](https://app.dealroom.co/companies/pensumo)
- [Diario Financiero (Chile) – Cotización vía consumo](https://www.df.cl/periodismo-de-soluciones/cotizacion-via-consumo-la-apuesta-para-mejorar-las-pensiones-que-gana)
- [Instituto Santalucía – La pensión por consumo (PDF)](https://institutosantalucia.es/wp-content/uploads/2024/10/c07_la_pension_por_consumo.pdf)
