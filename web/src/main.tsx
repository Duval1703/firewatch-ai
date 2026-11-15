import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Activity, AlertTriangle, ArrowDownToLine, CalendarDays, Check, ChevronDown,
  ChartNoAxesCombined, CircleHelp, Crosshair, Database, Flame, Gauge, Layers3,
  MessageSquareText, Send, Trash2,
  MapPinned, RadioTower, Satellite, ShieldCheck, SlidersHorizontal, X,
} from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import {
  CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMapEvents,
} from 'react-leaflet'
import type { LatLngTuple } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './style.css'

type Page = 'overview' | 'satellites' | 'calendar' | 'analytics' | 'anomalies' | 'links' | 'reports' | 'quality' | 'assistant'
type Source = { product_code: string; satellite: string; stream_type: string; records: number }
type Metadata = { date_min: string; date_max: string; total_records: number; sources: Source[]; limitations: string[] }
type SummarySource = { product_code: string; satellite: string; stream_type: string; detections: number }
type Summary = { total_detections: number; dates_with_rows: number; sources: SummarySource[] }
type CalendarRow = {
  date_utc: string; year_folder: string; product_code: string; satellite: string;
  stream_type: string; detection_count: number; has_observation_rows: boolean; activity_state: string
}
type MapCell = {
  latitude: number; longitude: number; satellite: string; product_code: string; stream_type: string;
  detection_count?: number; confidence_raw?: string; frp?: number | null
}
type MapResult = { total_detections: number; displayed_cells: number; sampled?: boolean; aggregation_degrees?: number | null; cells: MapCell[] }
type CandidateLink = {
  candidate_link_id: string; left_observation_id: string; right_observation_id: string;
  left_satellite: string; right_satellite: string; left_product_code: string; right_product_code: string;
  left_latitude: number; left_longitude: number; right_latitude: number; right_longitude: number;
  left_datetime_utc: string; right_datetime_utc: string; distance_km: number;
  time_difference_minutes: number; link_family: string; method_version: string
}
type CandidateResult = { total_candidate_links: number; returned_candidate_links: number; truncated: boolean; links: CandidateLink[] }
type Quality = {
  total_rows: number; validation_status: Record<string, number>; duplicate_observation_ids: number;
  missing_values: Record<string, number>; sources: Array<{year_folder: string; product_code: string; satellite: string; stream_type: string; records: number; source_files: number}>;
  date_min: string; date_max: string; source_files: number
}
type TrendRow = { month: string; product_code: string; satellite: string; stream_type: string; detection_count: number; dates_with_rows: number }

const COLORS: Record<string, string> = { 'M-C61': '#df8a48', 'SV-C2': '#91aa67', 'J1V-C2': '#44aaa0', 'J2V-C2': '#6e9fc7' }
const PRODUCT_LABELS: Record<string, string> = { 'M-C61': 'MODIS · Terra/Aqua', 'SV-C2': 'VIIRS · Suomi-NPP', 'J1V-C2': 'VIIRS · NOAA-20', 'J2V-C2': 'VIIRS · NOAA-21' }
const PLATFORMS: Record<string, { product: string; description: string; instrument: string }> = {
  Aqua: { product: 'M-C61', description: 'Afternoon MODIS observations from NASA’s Aqua platform.', instrument: 'MODIS · Collection 6.1' },
  Terra: { product: 'M-C61', description: 'Morning MODIS observations from NASA’s Terra platform.', instrument: 'MODIS · Collection 6.1' },
  SNPP: { product: 'SV-C2', description: 'Suomi-NPP VIIRS observations; confidence categories are product-specific.', instrument: 'VIIRS · 375 m active fire' },
  N20: { product: 'J1V-C2', description: 'NOAA-20 VIIRS observations; kept distinct from other VIIRS platforms.', instrument: 'VIIRS · 375 m active fire' },
  N21: { product: 'J2V-C2', description: 'NOAA-21 VIIRS observations; kept distinct from other VIIRS platforms.', instrument: 'VIIRS · 375 m active fire' },
}
const NAV: Array<{ id: Page; label: string; icon: typeof Activity; note: string }> = [
  { id: 'overview', label: 'Overview', icon: Activity, note: 'Live situation' },
  { id: 'satellites', label: 'Satellite explorer', icon: Satellite, note: 'Compare instruments' },
  { id: 'calendar', label: 'Activity calendar', icon: CalendarDays, note: 'Daily record' },
  { id: 'analytics', label: 'Fire analytics', icon: Gauge, note: 'Historical patterns' },
  { id: 'anomalies', label: 'Anomaly intelligence', icon: ChartNoAxesCombined, note: 'Explainable signals' },
  { id: 'links', label: 'Candidate links', icon: Layers3, note: 'Cross-sensor evidence' },
  { id: 'reports', label: 'Reports', icon: ArrowDownToLine, note: 'Export findings' },
  { id: 'quality', label: 'Data quality', icon: ShieldCheck, note: 'Lineage and checks' },
  { id: 'assistant', label: 'Data assistant', icon: MessageSquareText, note: 'Ask about this view' },
]
const fmt = (value: number) => new Intl.NumberFormat('en-US').format(value)
const median = (values: number[]) => {
  if (!values.length) return 0
  const sorted = [...values].sort((a, b) => a - b), middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}
const bounds = (month: string) => {
  const [year, monthNo] = month.split('-').map(Number)
  return [`${year}-${String(monthNo).padStart(2, '0')}-01`, new Date(Date.UTC(year, monthNo, 0)).toISOString().slice(0, 10)] as const
}
const queryFor = (start: string, end: string, satellites: string[], streams: string[]) => {
  const query = new URLSearchParams({ start, end })
  if (satellites.length) query.set('satellites', satellites.join(','))
  if (streams.length) query.set('streams', streams.join(','))
  return query.toString()
}
type ChatMessage = { role: 'assistant' | 'user'; text: string }
function answerDataQuestion(question: string, context: {
  month: string; selectedDay: string | null; summary: Summary | null; metadata: Metadata | null;
  satellites: string[]; allSatellites: string[]; streams: string[]; allStreams: string[];
  anomalyCount: number; anomalyCutoff: number; candidates: CandidateResult | null; quality: Quality | null; medianDaily: number; mad: number
}) {
  const q = question.toLowerCase()
  const period = context.selectedDay ? `${context.selectedDay} UTC` : `${context.month} UTC`
  const scope = `For ${period}, ${context.satellites.length ? context.satellites.join(', ') : 'all platforms'}, and ${context.streams.length ? context.streams.join(', ') : 'all streams'}:`
  const sources = context.summary?.sources ?? []
  if (/^(hi|hello|hey)\b/.test(q)) return 'Hello. Ask me about the current observation count, satellites, candidate links, anomaly flags, data quality, or how to interpret the record.'
  if (/candidate|overlap|associat|match|same fire/.test(q)) return context.candidates
    ? `${scope} the current association calculation returned ${fmt(context.candidates.total_candidate_links)} candidate observation pairs (${context.candidates.returned_candidate_links} available for review${context.candidates.truncated ? ', truncated at the service limit' : ''}). They are proximity-based leads, not confirmed shared fires or unique events.`
    : `${scope} candidate pairs have not been calculated on this page. Open Candidate links to calculate them for this date and filter selection. These pairs are review leads, not confirmed fires.`
  if (/anomal|unusual|spike|flag/.test(q)) return `For ${context.month} UTC, using the selected platform and stream filters, the robust daily-volume screen flags ${context.anomalyCount} day(s) at a cutoff of ${context.anomalyCutoff}. It compares the month's observed daily row counts using a median and median absolute deviation (MAD); choosing a day focuses the map and summary, but does not change this month-level screen. It is not a fire forecast.`
  if (/quality|missing|duplicate|validat|quarantin|complete/.test(q)) return context.quality
    ? `Across the loaded archive, ${fmt(context.quality.total_rows)} rows are present in ${fmt(context.quality.source_files)} files; ${fmt(context.quality.duplicate_observation_ids)} normalized observation IDs repeat. The quality page has field-level missingness and validation counts. These are archive-wide checks, while the map and summary use your current filters.`
    : 'The archive-wide quality summary has not been loaded yet. Open Data quality to inspect source counts, missing values, repeated IDs, and coordinate/time validation.'
  if (/which satellite|top satellite|most (detections|observations|active)|platform ranking|by satellite/.test(q)) {
    if (!sources.length) return `${scope} there are no matching rows to rank.`
    const ranked = [...sources].sort((a, b) => b.detections - a.detections).slice(0, 3)
    return `${scope} the leading platforms by source-row count are ${ranked.map((item, index) => `${index + 1}) ${item.satellite}: ${fmt(item.detections)}`).join('; ')}. Counts are observation rows, not distinct fires.`
  }
  if (/modis|viirs|confidence|frp|harmoni[sz]|instrument|resolution/.test(q)) return 'MODIS C6.1 observations come from Terra and Aqua; the VIIRS sources here are Suomi-NPP, NOAA-20, and NOAA-21. Their confidence categories and FRP values are product-specific, so FIREWATCH preserves those source values instead of combining them into a shared confidence score. Candidate cross-sensor links use space/time proximity and must be reviewed; they do not establish event identity.'
  if (/no rows|zero|empty day|coverage/.test(q)) return 'No matching rows means this extract has no observation records for that selection. It does not prove zero fire activity or confirm that the satellite had valid coverage.'
  if (/period|date range|how far|archive|available data/.test(q)) return context.metadata
    ? `The loaded archive spans ${context.metadata.date_min} through ${context.metadata.date_max}. The current view is ${period}. FIREWATCH keeps the original platform and processing stream visible.`
    : 'Source date coverage is still loading.'
  if (/count|how many|total|observation|detection|rows/.test(q)) return `${scope} ${fmt(context.summary?.total_detections ?? 0)} source observation rows appear across ${fmt(context.summary?.dates_with_rows ?? 0)} dates with rows. These are not counts of unique fires or burned area.`
  if (/median|mad|method|score|calculate/.test(q)) return `The anomaly screen uses daily observation-row volume for ${context.month}, with the current platform and stream filters. It calculates the median and median absolute deviation (MAD), then applies a robust score with cutoff ${context.anomalyCutoff}. The daily median is ${fmt(context.medianDaily)} rows and MAD is ${fmt(context.mad)}. This is an exploratory volume screen, not a seasonal anomaly model or forecast.`
  return 'I can answer questions grounded in the loaded FIREWATCH data: current counts and filters, platform comparisons, observation period, candidate links, anomaly screening, data quality, and MODIS/VIIRS interpretation. Try one of the suggested questions below.'
}
async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`Request failed (${response.status})`)
  return response.json() as Promise<T>
}
function saveCsv(filename: string, rows: Array<Record<string, unknown>>) {
  if (!rows.length) return
  const columns = [...new Set(rows.flatMap(row => Object.keys(row)))]
  const escape = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`
  const csv = [columns.map(escape).join(','), ...rows.map(row => columns.map(key => escape(row[key])).join(','))].join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click()
  URL.revokeObjectURL(url)
}
function ZoomWatcher({ onChange }: { onChange: (zoom: number) => void }) {
  useMapEvents({ zoomend(event) { onChange(event.target.getZoom()) } }); return null
}
function FireMap({ result, links, onZoom }: { result: MapResult | null; links?: CandidateLink[]; onZoom: (zoom: number) => void }) {
  const center: LatLngTuple = [7.5, 12.4]
  return <MapContainer center={center} zoom={6} minZoom={4} maxZoom={16} scrollWheelZoom className="fire-map">
    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <ZoomWatcher onChange={onZoom} />
    {(result?.cells ?? []).map((cell, i) => {
      const color = COLORS[cell.product_code] ?? '#df8a48'
      const radius = cell.detection_count ? Math.min(16, 3.2 + Math.sqrt(cell.detection_count) * 1.15) : 4.2
      return <CircleMarker key={`${cell.satellite}-${cell.latitude}-${cell.longitude}-${i}`} center={[cell.latitude, cell.longitude]} radius={radius}
        pathOptions={{ color, fillColor: color, fillOpacity: .7, weight: 1 }}>
        <Popup><strong>{cell.detection_count ? `${fmt(cell.detection_count)} detection rows` : 'Satellite detection'}</strong><br />{cell.satellite} · {cell.product_code}<br />{cell.stream_type.replace('_', ' ')}{cell.confidence_raw ? <><br />Source confidence: {cell.confidence_raw}</> : null}{cell.frp != null ? <><br />Source FRP: {cell.frp}</> : null}</Popup>
      </CircleMarker>
    })}
    {(links ?? []).filter(link => link.link_family === 'MODIS-VIIRS').slice(0, 350).map((link, i) => <Polyline key={link.candidate_link_id ?? i}
      positions={[[link.left_latitude, link.left_longitude], [link.right_latitude, link.right_longitude]]}
      pathOptions={{ color: '#e5a346', opacity: .62, weight: 1.5, dashArray: '4 5' }} />)}
  </MapContainer>
}
function Legend() { return <div className="map-legend">{Object.entries(PRODUCT_LABELS).map(([product, label]) => <span key={product}><i style={{ background: COLORS[product] }} />{label}</span>)}</div> }
function FirewatchMark({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <circle cx="20" cy="20" r="14.5" stroke="currentColor" strokeWidth="1.15" strokeOpacity=".55" />
    <circle cx="20" cy="20" r="8.5" stroke="currentColor" strokeWidth="1.15" strokeOpacity=".82" />
    <path d="M20 2.5v6M20 31.5v6M2.5 20h6M31.5 20h6" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
    <circle cx="20" cy="20" r="2.7" fill="#e6a05c" />
  </svg>
}
function PageHeading({ icon: Icon, title, subtitle, children }: { icon: typeof Activity; title: string; subtitle: string; children?: ReactNode }) {
  return <div className="page-heading"><div><div className="heading-kicker"><Icon size={15} /> FIRMS observation intelligence</div><h1>{title}</h1><p className="heading-sub">{subtitle}</p></div>{children}</div>
}
function Metric({ icon: Icon, value, label, detail, tone = 'orange' }: { icon: typeof Activity; value: string; label: string; detail?: string; tone?: string }) {
  return <article className={`metric-card metric-${tone}`}><span className="metric-icon"><Icon size={18} /></span><div><strong>{value}</strong><span>{label}</span>{detail && <small>{detail}</small>}</div></article>
}
function MapPanel({ result, links, onZoom, title = 'Detection map', subtitle, action }: { result: MapResult | null; links?: CandidateLink[]; onZoom: (zoom: number) => void; title?: string; subtitle?: string; action?: ReactNode }) {
  return <section className="panel map-panel"><div className="panel-heading map-heading"><div><div className="section-title"><Crosshair size={16} /><h2>{title}</h2></div><p>{subtitle ?? (result?.aggregation_degrees ? `Grouped to ${result.aggregation_degrees}° grid cells` : result?.sampled ? 'Showing a reproducible sample of individual detections' : 'Individual satellite observations')}</p></div>
    <div className="map-heading-actions">{action}<span className="map-count"><i />{fmt(result?.total_detections ?? 0)} rows</span></div></div><div className="map-wrap"><FireMap result={result} links={links} onZoom={onZoom} /></div><Legend /></section>
}

function App() {
  const [page, setPage] = useState<Page>(() => (NAV.some(item => item.id === location.hash.slice(1)) ? location.hash.slice(1) as Page : 'overview'))
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [quality, setQuality] = useState<Quality | null>(null)
  const [trends, setTrends] = useState<TrendRow[]>([])
  const [month, setMonth] = useState('2025-10')
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [satellites, setSatellites] = useState<string[]>([])
  const [streams, setStreams] = useState<string[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [calendar, setCalendar] = useState<CalendarRow[]>([])
  const [mapResult, setMapResult] = useState<MapResult | null>(null)
  const [candidates, setCandidates] = useState<CandidateResult | null>(null)
  const [showLinks, setShowLinks] = useState(false)
  const [distanceKm, setDistanceKm] = useState(1)
  const [timeHours, setTimeHours] = useState(3)
  const [family, setFamily] = useState('all')
  const [anomalyCutoff, setAnomalyCutoff] = useState(3.5)
  const [linkSearch, setLinkSearch] = useState('')
  const [zoom, setZoom] = useState(6)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [qualityError, setQualityError] = useState('')
  const [linkError, setLinkError] = useState('')
  const [toast, setToast] = useState('')
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([{ role: 'assistant', text: 'I answer from the NASA FIRMS observations and calculations loaded in this workspace. Your month, platform, stream, and day filters are shared with the map and analytics.' }])

  const allSatellites = useMemo(() => [...new Set(metadata?.sources.map(source => source.satellite) ?? [])].sort(), [metadata])
  const allStreams = useMemo(() => [...new Set(metadata?.sources.map(source => source.stream_type) ?? [])].sort(), [metadata])
  const [monthStart, monthEnd] = bounds(month)
  const queryStart = selectedDay ?? monthStart, queryEnd = selectedDay ?? monthEnd
  const activeNav = NAV.find(item => item.id === page) ?? NAV[0]

  const navigate = useCallback((next: Page, replace = false) => {
    if (location.hash !== `#${next}`) history[replace ? 'replaceState' : 'pushState']({}, '', `#${next}`)
    setPage(next); window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])
  useEffect(() => {
    const onPop = () => setPage(NAV.some(item => item.id === location.hash.slice(1)) ? location.hash.slice(1) as Page : 'overview')
    window.addEventListener('popstate', onPop)
    if (!location.hash) history.replaceState({}, '', '#overview')
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  useEffect(() => {
    getJson<Metadata>('/api/metadata').then(setMetadata).catch(() => setError('The FIRMS data service is unavailable. Start the API and reload this page.'))
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    setBusy(true); setError('')
    const monthQuery = queryFor(monthStart, monthEnd, satellites, streams)
    const selectedQuery = queryFor(queryStart, queryEnd, satellites, streams)
    Promise.all([
      getJson<Summary>(`/api/summary?${selectedQuery}`, controller.signal),
      getJson<CalendarRow[]>(`/api/calendar?${monthQuery}`, controller.signal),
      getJson<MapResult>(`/api/map?${selectedQuery}&zoom=${zoom}`, controller.signal),
    ]).then(([nextSummary, nextCalendar, nextMap]) => { setSummary(nextSummary); setCalendar(nextCalendar); setMapResult(nextMap) })
      .catch(reason => { if (reason.name !== 'AbortError') setError('The selected observations could not be loaded. Check the API and try again.') })
      .finally(() => { if (!controller.signal.aborted) setBusy(false) })
    return () => controller.abort()
  }, [monthStart, monthEnd, queryStart, queryEnd, satellites, streams, zoom])
  useEffect(() => {
    if (page !== 'quality' && page !== 'assistant') return
    const controller = new AbortController()
    getJson<Quality>('/api/quality', controller.signal).then(setQuality).catch(reason => { if (reason.name !== 'AbortError') setQualityError('Quality statistics could not be loaded.') })
    return () => controller.abort()
  }, [page])
  useEffect(() => {
    if (page !== 'analytics') return
    const controller = new AbortController()
    const query = queryFor(metadata?.date_min ?? '2025-01-01', metadata?.date_max ?? '2026-11-02', satellites, streams)
    getJson<TrendRow[]>(`/api/trends?${query}`, controller.signal).then(setTrends)
      .catch(reason => { if (reason.name !== 'AbortError') setError('Historical analytics could not be loaded.') })
    return () => controller.abort()
  }, [page, metadata, satellites, streams])
  useEffect(() => {
    if (page !== 'links' && page !== 'reports' && !showLinks) { setCandidates(null); setLinkError(''); return }
    const controller = new AbortController(); setLinkError('')
    setCandidates(null)
    const query = queryFor(queryStart, queryEnd, satellites, streams)
    getJson<CandidateResult>(`/api/candidate-links?${query}&max_distance_km=${distanceKm}&max_time_delta_hours=${timeHours}`, controller.signal)
      .then(setCandidates).catch(reason => { if (reason.name !== 'AbortError') setLinkError('Candidate links could not be calculated for this selection.') })
    return () => controller.abort()
  }, [page, showLinks, queryStart, queryEnd, satellites, streams, distanceKm, timeHours])
  useEffect(() => { if (!toast) return; const timer = window.setTimeout(() => setToast(''), 2600); return () => window.clearTimeout(timer) }, [toast])

  const calendarDays = useMemo(() => {
    const byDate = new Map<string, { date: string; detections: number; hasRows: boolean }>()
    for (const row of calendar) {
      const date = row.date_utc.slice(0, 10), current = byDate.get(date) ?? { date, detections: 0, hasRows: false }
      current.detections += row.detection_count; current.hasRows ||= row.has_observation_rows; byDate.set(date, current)
    }
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date))
  }, [calendar])
  const calendarCells = useMemo(() => {
    const [year, mon] = month.split('-').map(Number), firstWeekday = new Date(Date.UTC(year, mon - 1, 1)).getUTCDay()
    return [...Array(firstWeekday).fill(null), ...calendarDays]
  }, [month, calendarDays])
  const sources = summary?.sources ?? []
  const bySatellite = useMemo(() => {
    const grouped = new Map<string, { satellite: string; product_code: string; detections: number; archive: number; nrt: number }>()
    for (const item of sources) {
      const row = grouped.get(item.satellite) ?? { satellite: item.satellite, product_code: item.product_code, detections: 0, archive: 0, nrt: 0 }
      row.detections += item.detections; row[item.stream_type === 'archive' ? 'archive' : 'nrt'] += item.detections; grouped.set(item.satellite, row)
    }
    return [...grouped.values()].sort((a, b) => b.detections - a.detections)
  }, [sources])
  const filteredLinks = useMemo(() => (candidates?.links ?? []).filter(link => (family === 'all' || link.link_family === family)
    && (!linkSearch || `${link.left_satellite} ${link.right_satellite}`.toLowerCase().includes(linkSearch.toLowerCase()))), [candidates, family, linkSearch])
  const topLinks = filteredLinks.slice(0, 250)
  const coveragePercent = calendarDays.length ? Math.round(calendarDays.filter(day => day.hasRows).length / calendarDays.length * 100) : 0
  const monthlyData = useMemo(() => {
    const map = new Map<string, Record<string, number | string | boolean | null>>(), platforms = [...new Set(trends.map(row => row.satellite))].sort()
    const first = metadata?.date_min.slice(0, 7) ?? '2025-01', last = metadata?.date_max.slice(0, 7) ?? '2026-11'
    const [fy, fm] = first.split('-').map(Number), [ly, lm] = last.split('-').map(Number)
    for (let serial = fy * 12 + fm - 1; serial <= ly * 12 + lm - 1; serial++) {
      const date = `${Math.floor(serial / 12)}-${String(serial % 12 + 1).padStart(2, '0')}`
      const item: Record<string, number | string | boolean | null> = { month: date, total: 0, hasRows: false }
      platforms.forEach(platform => { item[platform] = null })
      map.set(date, item)
    }
    for (const row of trends) {
      const item = map.get(row.month)
      if (!item) continue
      item[row.satellite] = Number(item[row.satellite] ?? 0) + row.detection_count
      item.total = Number(item.total) + row.detection_count; item.hasRows = true
    }
    return [...map.values()]
  }, [trends, metadata])
  const selectedMonthNumber = Number(month.slice(5, 7))
  const selectedMonthYearTotals = useMemo(() => [2025, 2026].map(year => {
    const value = trends.filter(row => row.month === `${year}-${String(selectedMonthNumber).padStart(2, '0')}`).reduce((sum, row) => sum + row.detection_count, 0)
    return { year, value: trends.some(row => row.month === `${year}-${String(selectedMonthNumber).padStart(2, '0')}`) ? value : null }
  }), [trends, selectedMonthNumber])
  const observedDays = calendarDays.filter(day => day.hasRows).map(day => day.detections)
  const medianDaily = median(observedDays)
  const mad = median(observedDays.map(value => Math.abs(value - medianDaily)))
  const anomalyRows = mad > 0 ? calendarDays.filter(day => day.hasRows).map(day => ({ ...day, robustScore: .6745 * (day.detections - medianDaily) / mad })).filter(day => day.robustScore >= anomalyCutoff).sort((a, b) => b.robustScore - a.robustScore) : []
  const reportTimestamp = new Date().toLocaleString('en', { dateStyle: 'medium', timeStyle: 'short' })
  const quarantinedRows = Object.entries(quality?.validation_status ?? {}).filter(([status]) => status !== 'valid').reduce((sum, [, count]) => sum + count, 0)
  const toggleSatellite = (value: string) => {
    const active = satellites.length ? satellites : allSatellites
    if (active.includes(value) && active.length === 1) { setToast('Keep at least one satellite selected.'); return }
    const next = active.includes(value) ? active.filter(item => item !== value) : [...active, value]
    setSatellites(next.length === allSatellites.length ? [] : next); setSelectedDay(null)
  }
  const toggleStream = (value: string) => {
    const active = streams.length ? streams : allStreams
    if (active.includes(value) && active.length === 1) { setToast('Keep at least one processing stream selected.'); return }
    const next = active.includes(value) ? active.filter(item => item !== value) : [...active, value]
    setStreams(next.length === allStreams.length ? [] : next); setSelectedDay(null)
  }
  const exportLinks = () => saveCsv('firewatch_candidate_links.csv', filteredLinks.map(link => ({
    candidate_link_id: link.candidate_link_id, left_satellite: link.left_satellite, right_satellite: link.right_satellite,
    left_observation_utc: link.left_datetime_utc, right_observation_utc: link.right_datetime_utc,
    distance_km: link.distance_km, time_difference_minutes: link.time_difference_minutes,
    link_family: link.link_family, method_version: link.method_version,
  })))
  const askAssistant = (rawQuestion: string) => {
    const question = rawQuestion.trim()
    if (!question) return
    const context = { month, selectedDay, summary, metadata, satellites, allSatellites, streams, allStreams, anomalyCount: anomalyRows.length, anomalyCutoff, candidates, quality, medianDaily, mad }
    setChatMessages(current => [...current, { role: 'user', text: question }, { role: 'assistant', text: answerDataQuestion(question, context) }])
    setChatInput('')
  }

  const globalControls = <section className="global-controls" aria-label="Shared observation filters">
    <div className="global-control-top"><div className="filter-label"><SlidersHorizontal size={15} /><span>Shared filters</span><small>Platforms and streams sync · period follows the selected view</small></div>
      <div className="period-control"><CalendarDays size={16} /><label htmlFor="month-picker">Observation month · UTC</label><input id="month-picker" type="month" min="2025-01" max="2026-11" value={month} onChange={event => { setMonth(event.target.value); setSelectedDay(null) }} /></div>
    </div>
    <div className="filter-row"><div className="filter-label"><Satellite size={14} /><span>Platforms</span></div><div className="filter-group" aria-label="Satellite platform filters">{allSatellites.map(satellite => {
      const checked = !satellites.length || satellites.includes(satellite), source = metadata?.sources.find(item => item.satellite === satellite)
      return <button key={satellite} className={checked ? 'source-chip selected' : 'source-chip'} onClick={() => toggleSatellite(satellite)} aria-pressed={checked}><i style={{ background: COLORS[source?.product_code ?? ''] ?? '#afb8ad' }} />{satellite}</button>
    })}</div><div className="filter-divider" /><div className="filter-label stream-filter-label"><RadioTower size={14} /><span>Stream</span></div><div className="filter-group stream-group">{allStreams.map(stream => {
      const checked = !streams.length || streams.includes(stream)
      return <button key={stream} className={checked ? 'stream-chip selected' : 'stream-chip'} onClick={() => toggleStream(stream)} aria-pressed={checked}>{stream === 'archive' ? 'Archive' : 'Near real-time'}</button>
    })}</div>{selectedDay && <button className="clear-day" onClick={() => setSelectedDay(null)}><X size={13} /> {selectedDay}<span>Clear day</span></button>}</div>
  </section>

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#overview" onClick={event => { event.preventDefault(); navigate('overview') }} aria-label="FIREWATCH home"><span className="brand-mark"><FirewatchMark /></span><span className="brand-wordmark"><strong>FIREWATCH</strong><small>EARTH OBSERVATION</small></span></a>
      <div className="topbar-location"><MapPinned size={15} /><span>Cameroon</span><ChevronDown size={13} /></div><div className="topbar-spacer" /><div className="service-state"><span className={metadata ? 'service-dot online' : 'service-dot'} />{metadata ? `${fmt(metadata.total_records)} source rows connected` : 'Connecting to FIRMS data'}</div></header>
    <div className="app-body"><aside className="sidebar" aria-label="FIREWATCH modules"><div className="sidebar-heading"><span>FIRE INTELLIGENCE</span><small>Cameroon workspace</small></div>
      <nav className="sidebar-nav" aria-label="Main navigation">{NAV.map(item => { const Icon = item.icon; return <a key={item.id} href={`#${item.id}`} className={page === item.id ? 'sidebar-link active' : 'sidebar-link'} aria-current={page === item.id ? 'page' : undefined} onClick={event => { event.preventDefault(); navigate(item.id) }}><Icon size={17} /><span className="nav-link-copy"><strong>{item.label}</strong><small>{item.note}</small></span>{item.id === 'links' && showLinks && <i className="sidebar-status-dot" />}</a> })}</nav>
      <div className="sidebar-foot"><span className="sidebar-status-dot" />NASA FIRMS archive<br /><small>MODIS + three VIIRS sources</small></div></aside>
      <main className="workspace" key={page}>
        <div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>{activeNav.label}</strong><span className="breadcrumb-period">{selectedDay ?? month} · UTC</span></div>
        {globalControls}
        {error && <div className="error-banner" role="alert"><AlertTriangle size={16} />{error}<button onClick={() => window.location.reload()}>Reload</button></div>}

        {page === 'overview' && <>
          <PageHeading icon={Activity} title="Fire activity in Cameroon" subtitle="A live view of NASA satellite thermal-anomaly observations across the country." />
          <div className="metric-grid overview-metrics"><Metric icon={Flame} value={fmt(summary?.total_detections ?? 0)} label="Detection records" detail={selectedDay ? `On ${selectedDay}` : `Across ${month}`} /><Metric icon={CalendarDays} value={fmt(summary?.dates_with_rows ?? 0)} label="Dates with records" detail="UTC observation days" tone="teal" /><Metric icon={Satellite} value={String(satellites.length || allSatellites.length)} label="Platforms selected" detail="MODIS + VIIRS missions" tone="blue" /><Metric icon={Crosshair} value={fmt(mapResult?.displayed_cells ?? 0)} label="Map cells shown" detail={busy ? 'Refreshing selection…' : mapResult?.sampled ? 'Reproducible map sample' : 'Spatially aggregated view'} tone="green" /></div>
          <div className="overview-grid"><MapPanel result={mapResult} links={showLinks ? candidates?.links : undefined} onZoom={setZoom} subtitle={showLinks ? 'Dashed lines are proximity candidates; they are not confirmed shared fires.' : undefined} action={<button className={showLinks ? 'link-toggle active' : 'link-toggle'} onClick={() => setShowLinks(value => !value)} aria-pressed={showLinks}><Layers3 size={14} />{showLinks ? 'Hide links' : 'Show links'}</button>} />
            <div className="right-stack"><section className="panel source-panel"><div className="panel-heading"><div><div className="section-title"><RadioTower size={16} /><h2>Observations by platform</h2></div><p>Click a row to filter the whole workspace</p></div></div><SourceBars items={bySatellite} onToggle={toggleSatellite} satellites={satellites} /></section>
              <DailyChart days={calendarDays} selectedDay={selectedDay} onSelect={setSelectedDay} onOpenCalendar={() => navigate('calendar')} /></div></div>
          <div className="insight-ribbon"><span className="insight-glyph"><CircleHelp size={17} /></span><div><strong>Read detections as evidence, not fire counts</strong><p>Nearby observations can be associated for review. A candidate link is not an event identity, and an empty day does not establish clear satellite coverage.</p></div><button className="text-action" onClick={() => navigate('links')}>Review candidate links</button></div>
        </>}

        {page === 'assistant' && <>
          <PageHeading icon={MessageSquareText} title="FIREWATCH data assistant" subtitle="Ask focused questions about the observations and calculations in your current workspace." />
          <section className="assistant-context panel" aria-label="Assistant data scope">
            <div className="assistant-context-mark"><MessageSquareText size={18} /></div>
            <div><strong>Using the live workspace selection</strong><p>{selectedDay ?? month} UTC · {satellites.length ? satellites.join(', ') : 'all available platforms'} · {streams.length ? streams.join(', ') : 'all processing streams'}</p></div>
            <span className={busy ? 'assistant-live busy' : 'assistant-live'}><i />{busy ? 'Updating data' : 'Data connected'}</span>
          </section>
          <section className="assistant-panel panel" aria-label="Conversation with FIREWATCH data assistant">
            <div className="assistant-chat-head"><div><span className="assistant-avatar"><MessageSquareText size={17} /></span><div><strong>Observation analyst</strong><small>Answers are based on loaded data and documented methods</small></div></div><button type="button" className="assistant-clear" onClick={() => setChatMessages([{ role: 'assistant', text: 'Conversation cleared. Ask about the current observations, sources, associations, anomaly screen, or data quality.' }])} aria-label="Clear conversation"><Trash2 size={15} /> Clear</button></div>
            <div className="assistant-messages" role="log" aria-live="polite" aria-relevant="additions text">
              {chatMessages.map((message, index) => <article key={`${index}-${message.role}`} className={`assistant-message ${message.role}`}><span className="message-speaker">{message.role === 'assistant' ? 'FIREWATCH' : 'You'}</span><p>{message.text}</p></article>)}
            </div>
            <div className="assistant-prompts" aria-label="Suggested questions">{['How many observations are in this view?', 'Which satellite has the most rows?', 'What do candidate links mean?', 'How should I interpret no rows?'].map(prompt => <button key={prompt} type="button" onClick={() => askAssistant(prompt)}>{prompt}</button>)}</div>
            <form className="assistant-composer" onSubmit={event => { event.preventDefault(); askAssistant(chatInput) }}><label className="sr-only" htmlFor="assistant-question">Ask FIREWATCH about the data</label><input id="assistant-question" value={chatInput} onChange={event => setChatInput(event.target.value)} placeholder="Ask about this data selection…" autoComplete="off" /><button type="submit" disabled={!chatInput.trim()} aria-label="Send question"><Send size={17} /><span>Ask</span></button></form>
            <p className="assistant-footnote">Evidence-first answers · No generative model or external service is connected. Counts refer to observations, not confirmed fires.</p>
          </section>
        </>}

        {page === 'satellites' && <>
          <PageHeading icon={Satellite} title="Satellite explorer" subtitle="Compare where each instrument observed thermal anomalies, with original platform and stream labels preserved." />
          <div className="explorer-layout"><div className="explorer-map"><MapPanel result={mapResult} onZoom={setZoom} title="Platform observation map" /></div><aside className="explorer-rail"><div className="panel-heading explorer-title"><div><div className="section-title"><RadioTower size={16} /><h2>Platform comparison</h2></div><p>Choose a platform to filter the map</p></div></div><SourceBars items={bySatellite} onToggle={toggleSatellite} satellites={satellites} large />
            <div className="product-legend-block"><h3>Instrument families</h3><div><span className="product-swatch modis" /> <strong>MODIS Collection 6.1</strong><p>Terra and Aqua product family. Preserve source platform and original confidence representation.</p></div><div><span className="product-swatch viirs" /> <strong>VIIRS 375 m active fire</strong><p>Suomi-NPP, NOAA-20, and NOAA-21 remain separate platforms with their own processing histories.</p></div></div></aside></div>
          <section className="platform-grid">{allSatellites.map(satellite => { const info = PLATFORMS[satellite] ?? { product: '', description: 'Platform preserved as delivered by the source extract.', instrument: 'NASA FIRMS source' }, item = bySatellite.find(row => row.satellite === satellite), selected = !satellites.length || satellites.includes(satellite)
            return <button key={satellite} className={`platform-card ${selected ? '' : 'muted'}`} onClick={() => toggleSatellite(satellite)} aria-pressed={selected}><div className="platform-card-head"><span className="platform-dot" style={{ background: COLORS[info.product] ?? '#a9b3a9' }} /><strong>{satellite}</strong><span>{info.instrument}</span></div><div className="platform-count">{fmt(item?.detections ?? 0)} <small>rows in selection</small></div><p>{info.description}</p><div className="platform-streams"><span>Archive <b>{fmt(item?.archive ?? 0)}</b></span><span>Near real-time <b>{fmt(item?.nrt ?? 0)}</b></span></div></button>
          })}</section>
        </>}

        {page === 'calendar' && <>
          <PageHeading icon={CalendarDays} title="Activity calendar" subtitle="Inspect the observation record day by day. Dates without rows are marked as unknown coverage, not zero fire." ><button className="export-button" onClick={() => saveCsv(`firewatch_calendar_${month}.csv`, calendar.map(row => ({ ...row })))}><ArrowDownToLine size={15} /> Export calendar</button></PageHeading>
          <div className="calendar-layout"><section className="panel calendar-board"><div className="calendar-board-head"><div><strong>{new Date(`${month}-01T00:00:00Z`).toLocaleDateString('en', { month: 'long', year: 'numeric', timeZone: 'UTC' })}</strong><span>{fmt(summary?.total_detections ?? 0)} filtered records this {selectedDay ? 'selected day' : 'month'}</span></div><div className="calendar-key"><span><i className="key-hot" /> Observations</span><span><i className="key-unknown" /> No rows · unknown</span></div></div>
            <div className="calendar-grid weekday-row">{['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => <span key={day}>{day}</span>)}</div><div className="calendar-grid day-grid">{calendarCells.map((day, index) => day ? <button key={day.date} className={`day-cell ${day.hasRows ? 'has-observations' : 'unknown-day'} ${selectedDay === day.date ? 'day-selected' : ''}`} onClick={() => setSelectedDay(current => current === day.date ? null : day.date)} aria-pressed={selectedDay === day.date} aria-label={`${day.date}: ${day.hasRows ? `${fmt(day.detections)} observations` : 'no rows; coverage unknown'}`}><span>{Number(day.date.slice(-2))}</span>{day.hasRows ? <><i style={{ opacity: Math.max(.34, Math.min(.95, .34 + day.detections / Math.max(1, ...calendarDays.map(d => d.detections)) * .61)) }} /><small>{fmt(day.detections)}</small></> : <small className="unknown-label">—</small>}</button> : <div key={`blank-${index}`} className="day-cell blank-day" />)}</div>
            <div className="calendar-warning"><CircleHelp size={16} /><span>“No rows” means no matching record in this extract. It does not confirm zero fire activity or valid satellite coverage.</span></div></section>
            <aside className="calendar-side"><div className="metric-grid calendar-stats"><Metric icon={Flame} value={fmt(summary?.total_detections ?? 0)} label="Records selected" /><Metric icon={CalendarDays} value={`${coveragePercent}%`} label="Days with rows" tone="teal" /></div><DailyChart days={calendarDays} selectedDay={selectedDay} onSelect={setSelectedDay} /><section className="panel day-detail"><div className="section-title"><Crosshair size={15} /><h2>{selectedDay ?? 'Select a date'}</h2></div><p>{selectedDay ? (calendarDays.find(day => day.date === selectedDay)?.hasRows ? 'Source observations recorded on this UTC day.' : 'No matching source rows were delivered for this date; coverage is unknown.') : 'Choose a calendar day to focus the map and source totals.'}</p>{selectedDay && sources.length > 0 && <div className="detail-source-list">{sources.map(row => <span key={`${row.satellite}-${row.stream_type}`}><i style={{ background: COLORS[row.product_code] }} />{row.satellite}<b>{fmt(row.detections)}</b></span>)}</div>}<button className="secondary-action" onClick={() => navigate('overview')}>Open selected date on map</button></section></aside></div>
        </>}

        {page === 'analytics' && <>
          <PageHeading icon={Gauge} title="Fire activity analytics" subtitle="Explore the archive month by month and compare the recorded observation volume by satellite platform." />
          <div className="metric-grid quality-metrics"><Metric icon={Flame} value={fmt(trends.reduce((sum, row) => sum + row.detection_count, 0))} label="Filtered archive rows" detail="Current platform and stream filters" /><Metric icon={CalendarDays} value={fmt(monthlyData.filter(row => row.hasRows).length)} label="Months with source rows" detail="Across the delivered period" tone="teal" /><Metric icon={Satellite} value={String(new Set(trends.map(row => row.satellite)).size)} label="Platforms represented" detail="Distinct platform identifiers" tone="blue" /><Metric icon={Crosshair} value={fmt(monthlyData.filter(row => row.hasRows).length ? Math.round(trends.reduce((sum, row) => sum + row.detection_count, 0) / monthlyData.filter(row => row.hasRows).length) : 0)} label="Mean rows / observed month" detail="Detection records, not event counts" tone="green" /></div>
          <section className="panel analytics-chart-panel"><div className="panel-heading"><div><div className="section-title"><Activity size={16} /><h2>Monthly observations by platform</h2></div><p>Choose a month to update the rest of the workspace. Empty periods remain unfilled because coverage is unknown.</p></div><span className="unit-label">rows · UTC</span></div><div className="analytics-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={monthlyData} margin={{ top: 15, right: 18, bottom: 14, left: 5 }}><CartesianGrid vertical={false} stroke="#e5e8e2" /><XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: '#758078', fontSize: 9 }} interval={0} tickFormatter={value => `${String(value).slice(5)} '${String(value).slice(2, 4)}`} /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#758078', fontSize: 9 }} /><Tooltip labelFormatter={label => label} formatter={(value, name) => [value == null ? 'No rows · unknown coverage' : fmt(Number(value)), `${name} observations`]} />{allSatellites.map((platform, index) => { const product = metadata?.sources.find(source => source.satellite === platform)?.product_code ?? ''; return <Bar key={platform} dataKey={platform} stackId="sources" fill={COLORS[product] ?? '#89948c'} radius={index === allSatellites.length - 1 ? [3, 3, 0, 0] : undefined} cursor="pointer">{monthlyData.map(item => <Cell key={String(item.month)} stroke={item.month === month ? '#26352e' : 'none'} strokeWidth={item.month === month ? 1.5 : 0} onClick={() => { setMonth(String(item.month)); setSelectedDay(null) }} />)}</Bar>})}</BarChart></ResponsiveContainer></div><Legend /></section>
          <div className="analytics-lower"><section className="panel yoy-panel"><div className="panel-heading"><div><div className="section-title"><CalendarDays size={15} /><h2>Same-month comparison</h2></div><p>Recorded rows in the selected calendar month</p></div></div><div className="comparison-years">{selectedMonthYearTotals.map(item => <div key={item.year}><span>{item.year}</span><strong>{item.value == null ? 'No source rows' : fmt(item.value)}</strong><small>{item.value == null ? 'Coverage is unknown' : 'Observation records'}</small></div>)}</div><p className="comparison-caveat">Changes can reflect satellite coverage, data availability, platform mix, and processing. This is not a direct estimate of fire prevalence.</p></section><section className="panel source-analytics"><div className="panel-heading"><div><div className="section-title"><RadioTower size={15} /><h2>Platform totals</h2></div><p>Click a platform to compare it across the archive</p></div></div><SourceBars items={bySatellite} onToggle={toggleSatellite} satellites={satellites} /></section></div>
        </>}

        {page === 'anomalies' && <>
          <PageHeading icon={ChartNoAxesCombined} title="Anomaly intelligence" subtitle="A transparent screen for unusually high daily observation volume in the selected month." />
          <section className="anomaly-method panel"><div className="method-intro"><span><ChartNoAxesCombined size={17} /></span><div><strong>Robust within-month outlier screen</strong><p>Compares observed days in this month using the median and median absolute deviation (MAD). The modified robust Z-score highlights high-volume days only.</p></div></div><label>Robust score threshold <span><input type="number" min="2" max="5" step="0.5" value={anomalyCutoff} onChange={event => setAnomalyCutoff(Math.max(2, Math.min(5, Number(event.target.value) || 3.5)))} /></span></label><span className="method-version">modified Z ≥ {anomalyCutoff}</span></section>
          <div className="anomaly-caveat"><AlertTriangle size={17} /><p><strong>Interpretation limit:</strong> this is an observation-volume flag, not a fire-event or wildfire alarm. It does not adjust for satellite overpass, clear-sky coverage, or seasonal baselines. No rows remain unknown coverage and are excluded from its baseline.</p></div>
          <div className="metric-grid anomaly-metrics"><Metric icon={CalendarDays} value={fmt(observedDays.length)} label="Days with observations" detail="No-row days excluded" tone="teal" /><Metric icon={Activity} value={fmt(medianDaily)} label="Median rows / observed day" detail="Selected month and sources" tone="blue" /><Metric icon={Gauge} value={mad ? fmt(mad) : '0'} label="Median absolute deviation" detail="Robust dispersion estimate" tone="green" /><Metric icon={AlertTriangle} value={String(anomalyRows.length)} label="High-volume flags" detail={`Robust score ≥ ${anomalyCutoff}`} /></div>
          <div className="anomaly-layout"><section className="panel"><div className="panel-heading"><div><div className="section-title"><Activity size={15} /><h2>Daily counts and flagged days</h2></div><p>Choose a bar to focus other pages on that date</p></div></div><div className="analytics-chart anomaly-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={calendarDays.map(day => ({ ...day, label: day.date.slice(-2), anomaly: anomalyRows.some(row => row.date === day.date) }))} margin={{ top: 15, right: 15, bottom: 10, left: 0 }}><CartesianGrid vertical={false} stroke="#e5e8e2" /><XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#758078', fontSize: 9 }} interval="preserveStartEnd" /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#758078', fontSize: 9 }} /><Tooltip labelFormatter={(_label, payload) => payload?.[0]?.payload?.date ?? ''} formatter={(value, _name, item) => [`${fmt(Number(value ?? 0))} rows`, item.payload?.hasRows ? item.payload?.anomaly ? 'High observation-volume flag' : 'Observed detections' : 'No rows · coverage unknown']} /><Bar dataKey="detections" name="Observation rows" cursor="pointer" radius={[3, 3, 0, 0]}>{calendarDays.map(day => <Cell key={day.date} fill={anomalyRows.some(row => row.date === day.date) ? '#b95135' : day.hasRows ? '#d99a55' : '#dfe3dd'} onClick={() => day.hasRows && setSelectedDay(day.date)} />)}</Bar></BarChart></ResponsiveContainer></div></section><section className="panel anomaly-list"><div className="panel-heading"><div><div className="section-title"><AlertTriangle size={15} /><h2>Review flags</h2></div><p>Sorted by robust score</p></div></div>{observedDays.length < 14 ? <div className="empty-state">At least 14 observed days are needed for this exploratory screen. Current selection has {observedDays.length}.</div> : mad === 0 ? <div className="empty-state">The month has no measurable median absolute deviation. The robust score is undefined, so no anomaly flags are issued.</div> : anomalyRows.length ? <div className="flag-list">{anomalyRows.map(row => <button key={row.date} onClick={() => setSelectedDay(row.date)}><span>{row.date}</span><strong>{fmt(row.detections)} rows</strong><small>Robust Z {row.robustScore.toFixed(2)}</small></button>)}</div> : <div className="empty-state">No observed day exceeds the current threshold for this selection.</div>}</section></div>
          <section className="panel baseline-note"><h2>Why this model stays modest</h2><p>Two calendar years do not provide a robust multi-year seasonal baseline for each month. FIREWATCH therefore labels this result as a within-month observation-volume outlier screen. It does not train a forecast model, infer fire severity, or treat missing rows as zero activity.</p></section>
        </>}

        {page === 'links' && <>
          <PageHeading icon={Layers3} title="Candidate links" subtitle="Review observations that fall within explicit distance and overpass-time limits. Each pair is auditable evidence, not a confirmed fire." ><button className="export-button" onClick={exportLinks} disabled={!filteredLinks.length}><ArrowDownToLine size={15} /> Export {fmt(filteredLinks.length)} pairs</button></PageHeading>
          <section className="link-method panel"><div className="method-intro"><span><Layers3 size={18} /></span><div><strong>Transparent space-time association</strong><p>Each row connects two different satellite platforms. Raw detections remain unchanged; no event clustering or fire-probability score is implied.</p></div></div><label>Max distance <span><input type="number" min="0.1" max="5" step="0.1" value={distanceKm} onChange={event => setDistanceKm(Math.max(.1, Math.min(5, Number(event.target.value) || .1)))} /> km</span></label><label>Max overpass gap <span><input type="number" min="0.25" max="12" step="0.25" value={timeHours} onChange={event => setTimeHours(Math.max(.25, Math.min(12, Number(event.target.value) || .25)))} /> hours</span></label><span className="method-version">candidate-links-0.1.0</span></section>
          {linkError && <div className="error-banner" role="alert"><AlertTriangle size={16} />{linkError}</div>}
          <div className="link-summary-row"><Metric icon={Layers3} value={fmt(candidates?.total_candidate_links ?? 0)} label="Candidate pairs" detail={busy ? 'Refreshing selection…' : 'Under current limits'} tone="orange" /><Metric icon={Satellite} value={fmt(candidates?.returned_candidate_links ?? 0)} label="Pairs returned" detail={candidates?.truncated ? 'API result capped at 5,000' : 'Complete for this selection'} tone="teal" /><Metric icon={Gauge} value={`${distanceKm} km · ${timeHours} h`} label="Association window" detail="Editable parameters" tone="blue" /></div>
          <div className="links-layout"><MapPanel result={mapResult} links={candidates?.links} onZoom={setZoom} title="Candidate pair geography" subtitle="Dashed lines show MODIS–VIIRS candidate edges (up to 350 rendered)." /><section className="panel link-table-panel"><div className="table-heading"><div><div className="section-title"><Database size={16} /><h2>Pair evidence</h2></div><p>Showing {fmt(topLinks.length)} of {fmt(filteredLinks.length)} matching pairs</p></div><span className="unit-label">UTC</span></div><div className="table-tools"><input aria-label="Filter candidate pairs by satellite" placeholder="Filter by satellite…" value={linkSearch} onChange={event => setLinkSearch(event.target.value)} /><select aria-label="Filter candidate family" value={family} onChange={event => setFamily(event.target.value)}><option value="all">All platform families</option><option value="MODIS-VIIRS">MODIS ↔ VIIRS</option><option value="VIIRS-platform">VIIRS ↔ VIIRS</option><option value="MODIS-platform">MODIS ↔ MODIS</option></select></div>
            <div className="table-scroll"><table><thead><tr><th>Observations</th><th>Time separation</th><th>Distance</th><th>Pair type</th></tr></thead><tbody>{topLinks.map(link => <tr key={link.candidate_link_id}><td><strong>{link.left_satellite}</strong><span>↔</span><strong>{link.right_satellite}</strong><small>{new Date(link.left_datetime_utc).toISOString().slice(0, 16).replace('T', ' ')} UTC<br />{new Date(link.right_datetime_utc).toISOString().slice(0, 16).replace('T', ' ')} UTC</small></td><td>{link.time_difference_minutes.toFixed(0)} min</td><td>{link.distance_km.toFixed(3)} km</td><td><span className="family-pill">{link.link_family}</span></td></tr>)}</tbody></table>{!topLinks.length && <div className="empty-state">{busy ? 'Calculating candidate pairs…' : linkError ? 'Candidate calculation is unavailable.' : 'No candidate pairs meet these limits. Try a wider distance or time window.'}</div>}</div><div className="table-foot">Proximity is not event identity. Source confidence, masks, and observation lineage must be reviewed independently.</div></section></div>
        </>}

        {page === 'reports' && <>
          <PageHeading icon={ArrowDownToLine} title="Reports & export" subtitle="Create a printable record of the active filters and real FIRMS observations. Save the print view as PDF or export the underlying CSV." ><button className="export-button" onClick={() => window.print()} disabled={!candidates && !linkError}><ArrowDownToLine size={15} />{!candidates && !linkError ? 'Preparing report…' : 'Print / save PDF'}</button></PageHeading>
          <div className="report-actions"><button className="export-button" onClick={() => saveCsv(`firewatch_daily_${month}.csv`, calendar.map(row => ({ date_utc: row.date_utc, satellite: row.satellite, product_code: row.product_code, stream_type: row.stream_type, detection_count: row.detection_count, has_observation_rows: row.has_observation_rows, activity_state: row.activity_state })))}><ArrowDownToLine size={15} /> Export daily source rows</button><button className="export-button" onClick={() => saveCsv(`firewatch_satellites_${month}.csv`, bySatellite.map(row => ({ ...row })))}><ArrowDownToLine size={15} /> Export platform summary</button></div>
          <article className="report-document panel"><div className="report-doc-head"><div><div className="heading-kicker"><FirewatchMark className="report-brand-mark" /> FIREWATCH | OBSERVATION REPORT</div><h2>Satellite fire observations - Cameroon</h2><p>Prepared {reportTimestamp} | Period {selectedDay ?? `${monthStart} to ${monthEnd}`} | UTC</p></div><span className="report-stamp">NASA FIRMS<br />MODIS + VIIRS</span></div><div className="report-rule" /><div className="report-context"><span>Platforms: {satellites.length ? satellites.join(', ') : allSatellites.join(', ') || 'Loading'}</span><span>Streams: {streams.length ? streams.join(', ') : allStreams.join(', ') || 'Loading'}</span><span>Source archive: {metadata?.date_min ?? 'unavailable'} to {metadata?.date_max ?? 'unavailable'}</span></div><h3>Observed activity</h3><p>FIRMS supplied <strong>{fmt(summary?.total_detections ?? 0)} observation rows</strong> matching this selection, distributed across <strong>{fmt(summary?.dates_with_rows ?? 0)} dates</strong>. These are source observations and are not counts of unique fires or burned area.</p><div className="report-mini-metrics"><div><strong>{fmt(summary?.total_detections ?? 0)}</strong><span>Source rows</span></div><div><strong>{fmt(mapResult?.displayed_cells ?? 0)}</strong><span>Map cells / points</span></div><div><strong>{new Set(sources.map(source => source.satellite)).size}</strong><span>Platform groups</span></div></div><h3>Platform breakdown</h3><div className="report-platform-list">{bySatellite.map(row => <div key={row.satellite}><span><i style={{ background: COLORS[row.product_code] }} />{row.satellite} | {row.product_code}</span><b>{fmt(row.detections)}</b></div>)}</div><h3>Cross-sensor association review</h3><p>{linkError ? 'Candidate-link calculation was unavailable for this report.' : candidates ? `${fmt(candidates.total_candidate_links)} observation pairs meet the ${distanceKm} km and ${timeHours} hour proximity rule.` : 'Candidate associations are being calculated.'} Pairs are review evidence, not event counts or confirmed fires.</p><h3>Daily observation-volume screen</h3><p>{observedDays.length} observed days; median {fmt(medianDaily)} rows per day; median absolute deviation {fmt(mad)}. The exploratory robust threshold is 3.5. {anomalyRows.length ? `${anomalyRows.length} high-volume flag(s) were identified.` : 'No high-volume flags were identified under this rule.'} This screen is not a seasonal anomaly or fire forecast.</p><h3>Coverage and scientific limitations</h3><ul><li>No rows indicate unknown satellite coverage and must not be read as zero fire activity.</li><li>Archive and near-real-time records can be successive processing versions; the streams are shown separately.</li><li>MODIS and VIIRS confidence and FRP values are not combined into a common score.</li><li>Spatial-temporal candidate links are possible associations only. This report does not claim confirmed fires or validated event clusters.</li></ul><div className="report-sources">Data: NASA Fire Information for Resource Management System (FIRMS), supplied local CSV archive. Map basemap: OpenStreetMap contributors. Report generated by FIREWATCH AI.</div></article>
        </>}

        {page === 'quality' && <>
          <PageHeading icon={ShieldCheck} title="Data quality & provenance" subtitle="Inspect measurable checks on the loaded archive, with source files and platform lineage kept visible." ><button className="export-button" disabled={!quality} onClick={() => saveCsv('firewatch_source_inventory.csv', quality?.sources ?? [])}><ArrowDownToLine size={15} /> Export source inventory</button></PageHeading>
          {qualityError && <div className="error-banner" role="alert">{qualityError}</div>}
          <div className="quality-banner"><span><Check size={20} /></span><div><strong>{quality ? `${fmt(quality.validation_status.valid ?? 0)} records pass coordinate and timestamp validation` : 'Loading quality checks'}</strong><p>Current archive snapshot · {quality?.date_min ?? metadata?.date_min} to {quality?.date_max ?? metadata?.date_max} · read-only quality summary</p></div><span className="quality-badge">{quality ? 'INSPECTED' : 'LOADING'}</span></div>
          <div className="metric-grid quality-metrics"><Metric icon={Database} value={fmt(quality?.total_rows ?? metadata?.total_records ?? 0)} label="Source observations" detail="Original rows retained" tone="blue" /><Metric icon={Layers3} value={fmt(quality?.source_files ?? 0)} label="Source files" detail="Distinct input filenames" tone="teal" /><Metric icon={AlertTriangle} value={fmt(quarantinedRows)} label="Quarantined rows" detail="Invalid core fields" tone="orange" /><Metric icon={Crosshair} value={fmt(quality?.duplicate_observation_ids ?? 0)} label="Duplicate IDs" detail="Repeated normalized IDs" tone="green" /></div>
          <div className="quality-grid"><section className="panel inventory-panel"><div className="panel-heading"><div><div className="section-title"><Database size={16} /><h2>Source inventory</h2></div><p>Counts grouped by year, product, platform, and stream</p></div></div><div className="table-scroll inventory-scroll"><table><thead><tr><th>Year</th><th>Product</th><th>Platform</th><th>Stream</th><th>Rows</th><th>Files</th></tr></thead><tbody>{(quality?.sources ?? []).map((row, i) => <tr key={`${row.year_folder}-${row.satellite}-${row.stream_type}-${i}`}><td>{row.year_folder}</td><td><span className="product-code">{row.product_code}</span></td><td><i className="inventory-dot" style={{ background: COLORS[row.product_code] }} />{row.satellite}</td><td>{row.stream_type === 'archive' ? 'Archive' : 'Near real-time'}</td><td><strong>{fmt(row.records)}</strong></td><td>{fmt(row.source_files)}</td></tr>)}</tbody></table>{!quality && <div className="empty-state">Loading source inventory from the data service…</div>}</div></section>
            <aside className="quality-rail"><section className="panel integrity-panel"><div className="panel-heading"><div><div className="section-title"><Check size={16} /><h2>Field completeness</h2></div><p>Missing values in loaded observations</p></div></div><div className="integrity-list">{Object.entries(quality?.missing_values ?? {}).map(([field, missing]) => <div key={field}><span>{field.replaceAll('_', ' ')}</span><b className={missing ? 'quality-nonzero' : ''}>{fmt(missing)}</b><small>{missing ? 'missing' : 'complete'}</small></div>)}</div></section>
              <section className="panel lineage-panel"><div className="panel-heading"><div><div className="section-title"><CircleHelp size={16} /><h2>Interpret with care</h2></div></div></div><ul><li>A hotspot is a thermal-anomaly observation, not a confirmed wildfire.</li><li>MODIS and VIIRS confidence fields have different meanings; no cross-sensor confidence score is calculated.</li><li>Archive and near-real-time processing streams can contain successive versions of observations.</li><li>Dates without rows indicate unknown coverage, not zero fire.</li></ul><button className="secondary-action" onClick={() => navigate('links')}>Review the association method</button></section></aside></div>
        </>}
        <footer className="page-footer"><span>NASA FIRMS active-fire observations</span><span>{metadata ? `${fmt(metadata.total_records)} source rows · ${metadata.date_min} — ${metadata.date_max}` : 'Waiting for source metadata'}</span><span>UTC timestamps · Cameroon demo area</span></footer>
      </main></div>
    {toast && <div className="toast" role="status">{toast}</div>}
  </div>
}

function SourceBars({ items, onToggle, satellites, large = false }: { items: Array<{satellite: string; product_code: string; detections: number; archive: number; nrt: number}>; onToggle: (value: string) => void; satellites: string[]; large?: boolean }) {
  const max = Math.max(1, ...items.map(item => item.detections))
  return <div className={`source-bars ${large ? 'source-bars-large' : ''}`}>{items.length ? items.map(item => {
    const selected = !satellites.length || satellites.includes(item.satellite)
    return <button key={item.satellite} className={`source-bar-row ${selected ? '' : 'source-bar-muted'}`} onClick={() => onToggle(item.satellite)} aria-pressed={selected}><span className="source-bar-label"><i style={{ background: COLORS[item.product_code] }} />{item.satellite}<small>{item.satellite in PLATFORMS ? PLATFORMS[item.satellite].instrument.split(' · ')[0] : ''}</small></span><span className="bar-track"><i style={{ width: `${Math.max(1, item.detections / max * 100)}%`, background: COLORS[item.product_code] }} /></span><strong>{fmt(item.detections)}</strong>{large && <small className="source-stream-note">Archive {fmt(item.archive)} · NRT {fmt(item.nrt)}</small>}</button>
  }) : <div className="empty-state">No observations match these filters.</div>}</div>
}
function DailyChart({ days, selectedDay, onSelect, onOpenCalendar }: { days: Array<{date: string; detections: number; hasRows: boolean}>; selectedDay: string | null; onSelect: (day: string | null) => void; onOpenCalendar?: () => void }) {
  const data = days.map(item => ({ ...item, label: item.date.slice(-2) }))
  return <section className="panel daily-panel"><div className="panel-heading compact-heading"><div><div className="section-title"><Activity size={15} /><h2>Daily activity</h2></div><p>Choose a day to focus this workspace</p></div><span className="unit-label">UTC</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 8, right: 7, bottom: 5, left: -18 }}><CartesianGrid vertical={false} stroke="#e5e8e2" /><XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#758078', fontSize: 10 }} interval="preserveStartEnd" /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#758078', fontSize: 10 }} width={36} /><Tooltip labelFormatter={(_label, payload) => payload?.[0]?.payload?.date ?? ''} formatter={(value, _name, item) => [`${fmt(Number(value ?? 0))} rows`, item.payload?.hasRows ? 'Detections' : 'No rows · coverage unknown']} /><Bar dataKey="detections" name="Detection rows" radius={[3, 3, 0, 0]} cursor="pointer">{data.map(item => <Cell key={item.date} fill={selectedDay === item.date ? '#c75d3b' : item.hasRows ? '#e29a4f' : '#dfe3dd'} onClick={() => onSelect(selectedDay === item.date ? null : item.date)} />)}</Bar></BarChart></ResponsiveContainer></div><div className="chart-foot"><span>Pale bars mean no source rows; coverage is unknown.</span>{onOpenCalendar && <button onClick={onOpenCalendar}>Open calendar</button>}</div></section>
}

export default App
