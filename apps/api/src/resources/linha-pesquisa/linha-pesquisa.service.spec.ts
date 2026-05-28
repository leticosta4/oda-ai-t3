import { Test, TestingModule } from '@nestjs/testing';
import { LinhaPesquisaService } from './linha-pesquisa.service';

describe('LinhaPesquisaService', () => {
  let service: LinhaPesquisaService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [LinhaPesquisaService],
    }).compile();

    service = module.get<LinhaPesquisaService>(LinhaPesquisaService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
