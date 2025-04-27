/**
 * 통합 검색 관련 자바스크립트
 */

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
    // 날짜 범위 선택기 초기화
    initDateRangePicker();
    
    // 검색 폼 초기화
    initSearchForm();
    
    // 검색어 자동 완성 초기화 (필요한 경우)
    // initSearchAutocomplete();
});

// 날짜 범위 선택기 초기화 함수
function initDateRangePicker() {
    const dateRangeInput = document.getElementById('date_range');
    
    if (dateRangeInput) {
        // Flatpickr 설정으로 날짜 범위 선택기 초기화
        const picker = flatpickr(dateRangeInput, {
            mode: 'range',
            locale: 'ko',
            dateFormat: 'Y-m-d',
            rangeSeparator: ' ~ ',
            disableMobile: true,
            maxDate: new Date(),
            onClose: function() {
                // 날짜 선택 후 검색 폼 자동 제출
                if (dateRangeInput.value) {
                    document.getElementById('searchForm').submit();
                }
            }
        });
        
        // 빠른 날짜 선택 버튼 추가
        addQuickDateButtons(dateRangeInput, picker);
    }
}

// 빠른 날짜 선택 버튼 추가 함수
function addQuickDateButtons(dateRangeInput, picker) {
    const today = new Date();
    const container = document.createElement('div');
    container.className = 'quick-date-buttons mt-2';
    
    // 버튼 데이터 정의
    const buttons = [
        { text: '오늘', value: '오늘' },
        { text: '최근 일주일', value: '최근 일주일' },
        { text: '최근 한달', value: '최근 한달' },
        { text: '초기화', value: '' }
    ];
    
    // 버튼 생성 및 추가
    buttons.forEach(btn => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-sm btn-outline-secondary me-1';
        button.textContent = btn.text;
        
        // 버튼 클릭 이벤트
        button.addEventListener('click', function() {
            dateRangeInput.value = btn.value;
            
            // '초기화' 버튼이 아닌 경우 폼 제출
            if (btn.value !== '') {
                document.getElementById('searchForm').submit();
            }
        });
        
        container.appendChild(button);
    });
    
    // 날짜 선택기 다음에 버튼 컨테이너 추가
    dateRangeInput.parentNode.appendChild(container);
}

// 검색 폼 초기화 함수
function initSearchForm() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('search');
    const statusSelect = document.getElementById('status');
    
    if (searchForm && searchInput) {
        // 엔터 키로 검색 폼 제출
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchForm.submit();
            }
        });
        
        // 검색 입력에 포커스 시 도움말 표시
        searchInput.addEventListener('focus', function() {
            searchInput.setAttribute('placeholder', '주문번호, 고객사, 담당자, 상태 등 검색어 입력');
        });
        
        // 포커스 잃을 때 기본 플레이스홀더로 복원
        searchInput.addEventListener('blur', function() {
            searchInput.setAttribute('placeholder', '주문번호, 고객사, 담당자, 상태 등으로 검색');
        });
    }
    
    // 상태 선택 시 자동 폼 제출
    if (statusSelect) {
        statusSelect.addEventListener('change', function() {
            searchForm.submit();
        });
    }
} 